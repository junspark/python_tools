#!/usr/bin/env python3
"""
Offscreen smoke test for disk_monitor_gui, focused on TopFoldersDialog's
close/cancel lifecycle - reported directly in production as a crash:

  RuntimeError: wrapped C/C++ object of type QThread has been deleted

Root cause: closing the dialog after its scan had *already finished
naturally* (the common case - only a genuinely huge mount takes long
enough to still be running when closed) touched self._thread's live Qt
state, but the thread's own finished-signal-triggered deleteLater() had
already destroyed the underlying C++ object by then. Fixed by tracking
completion via a plain Python flag (_scan_done) set from the finished/
error signal handlers, never re-querying the QThread object once it may
have wound down.
"""

import json
import os
import sys
import tempfile
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5 import QtWidgets

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import disk_monitor_gui as dmg


def _make_tree(root, n_subdirs=50, n_files=100):
    for i in range(n_subdirs):
        sub = os.path.join(root, f"sub{i}")
        os.makedirs(sub)
        for j in range(n_files):
            with open(os.path.join(sub, f"f{j}.bin"), "wb") as f:
                f.write(b"\0" * 100)


def test_top_folders_close_after_scan_finished():
    """The exact bug: close a TopFoldersDialog whose scan already finished
    on its own before the user got to it."""
    print("Testing TopFoldersDialog close after scan already finished...", end=" ")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    with tempfile.TemporaryDirectory() as td:
        _make_tree(td)
        dlg = dmg.TopFoldersDialog(None, "test", td)
        dlg.show()

        for _ in range(200):
            app.processEvents()
            if dlg._scan_done:
                break
            time.sleep(0.01)
        assert dlg._scan_done, "scan should have finished well within this loop"
        # Let deleteLater()'s deferred deletion actually run before closing -
        # this is what made the original bug reproducible.
        app.processEvents()
        time.sleep(0.05)
        app.processEvents()

        dlg.reject()  # must not raise
        dlg._cancel_and_wait()  # calling cleanup again must also not raise

    print("✓")


def test_top_folders_cancel_mid_scan():
    """The original scenario this dialog's cancel button was built for:
    closing while du is still genuinely running."""
    print("Testing TopFoldersDialog cancel while scan is still running...", end=" ")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    with tempfile.TemporaryDirectory() as td:
        _make_tree(td, n_subdirs=200, n_files=200)
        dlg = dmg.TopFoldersDialog(None, "test2", td)
        dlg.show()
        app.processEvents()
        assert not dlg._scan_done, "expected the scan to still be running at this point"

        dlg.reject()  # must not raise, must actually cancel and return promptly

    print("✓")


def _write_panel_config(tmpdir, target_dirs):
    config_path = os.path.join(tmpdir, "config.json")
    config = {
        "settings": {
            "check_interval_sec": 3600,  # avoid the refresh timer firing mid-test
            "history_file": os.path.join(tmpdir, "history.jsonl"),
            "state_file": os.path.join(tmpdir, "state.json"),
        },
        "targets": [
            {"name": name, "path": path, "warn_pct": 90, "threshold_pct": 95}
            for name, path in target_dirs
        ],
    }
    with open(config_path, "w") as f:
        json.dump(config, f)
    return config_path


def test_recent_activity_column_populates():
    """DiskMonitorPanel's 'Recent activity' column starts as a placeholder
    and fills in from the background scan (_TopFoldersBackgroundScanner)
    without the caller needing to click "Top folders..." at all."""
    print("Testing 'Recent activity' column populates from background scan...", end=" ")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    with tempfile.TemporaryDirectory() as tmpdir:
        target_a = os.path.join(tmpdir, "target_a")
        target_b = os.path.join(tmpdir, "target_b")
        os.makedirs(target_a)
        os.makedirs(target_b)
        _make_tree(target_a, n_subdirs=5, n_files=5)
        _make_tree(target_b, n_subdirs=5, n_files=5)

        config_path = _write_panel_config(tmpdir, [("target_a", target_a), ("target_b", target_b)])
        panel = dmg.DiskMonitorPanel(config_path, show_font_control=False)

        activity_col = len(dmg.COLUMNS) - 1
        # Immediately after construction, both rows should show the
        # "not scanned yet" placeholder, not a blank cell.
        assert panel.table.item(0, activity_col).text() == "Scanning..."

        for _ in range(300):
            app.processEvents()
            if panel._activity_scan_done:
                break
            time.sleep(0.01)
        assert panel._activity_scan_done, "background activity scan should finish quickly for tiny test trees"

        for row in range(panel.table.rowCount()):
            text = panel.table.item(row, activity_col).text()
            assert text != "Scanning...", f"row {row} never got a real activity summary: {text!r}"
            assert "sub" in text, f"expected a 'subN (... ago)' summary, got {text!r}"

        panel.shutdown()  # must not raise, even though the scan already finished

    print("✓")


def test_top_folder_summary_ranks_size_and_recency_independently():
    """_top_folder_summary must rank by size and by recency separately,
    not just re-sort a size-based top N - a small folder edited seconds
    ago should show up in the 'recent' ranking even though it would never
    make a size-based top 3."""
    print("Testing _top_folder_summary ranks size and recency independently...", end=" ")

    now = 1_700_000_000
    entries = [
        {"name": "huge_old", "path": "/x/huge_old", "size_bytes": 500 * dmg.dm.GB, "mtime": now - 300 * 86400},
        {"name": "big_old", "path": "/x/big_old", "size_bytes": 300 * dmg.dm.GB, "mtime": now - 200 * 86400},
        {"name": "mid_old", "path": "/x/mid_old", "size_bytes": 100 * dmg.dm.GB, "mtime": now - 100 * 86400},
        {"name": "small_new", "path": "/x/small_new", "size_bytes": 1 * dmg.dm.GB, "mtime": now},
    ]
    orig_time = dmg.time.time
    dmg.time.time = lambda: now
    try:
        cell_text, tooltip = dmg._top_folder_summary(entries)
    finally:
        dmg.time.time = orig_time

    assert "small_new" in cell_text, f"cell should show the most recently touched folder, got {cell_text!r}"

    size_section = tooltip.split("Top 3 most recently edited:")[0]
    recency_section = tooltip.split("Top 3 most recently edited:")[1]
    assert "small_new" not in size_section, "small_new is smallest of the four, must not appear in the size ranking"
    assert "huge_old" in size_section and "big_old" in size_section and "mid_old" in size_section
    assert "small_new" in recency_section, "small_new is most recent, must appear in the recency ranking even though it's tiny"

    print("✓")


def test_panel_shutdown_mid_scan():
    """Closing the panel (e.g. the whole ops_gui window) while the
    background activity scan is still running must not crash - same
    QThread-lifetime class of bug as TopFoldersDialog, fixed the same way
    (a plain _activity_scan_done flag, never re-querying the QThread)."""
    print("Testing DiskMonitorPanel.shutdown() while activity scan is still running...", end=" ")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "big_target")
        os.makedirs(target)
        _make_tree(target, n_subdirs=300, n_files=300)

        config_path = _write_panel_config(tmpdir, [("big_target", target)])
        panel = dmg.DiskMonitorPanel(config_path, show_font_control=False)
        app.processEvents()
        assert not panel._activity_scan_done, "expected the scan to still be running at this point"

        panel.shutdown()  # must not raise, and must not hang
        assert panel._activity_scan_done

    print("✓")


if __name__ == "__main__":
    try:
        test_top_folders_close_after_scan_finished()
        test_top_folders_cancel_mid_scan()
        test_top_folder_summary_ranks_size_and_recency_independently()
        test_recent_activity_column_populates()
        test_panel_shutdown_mid_scan()
        print("\nGUI smoke tests passed! ✓")
    except Exception as e:
        print(f"\nGUI test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
