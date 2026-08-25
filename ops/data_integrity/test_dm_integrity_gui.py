#!/usr/bin/env python3
"""
Offscreen smoke test for dm_integrity_gui standalone and in combined ops_gui.
"""

import json
import os
import sys
import tempfile
import time
from unittest import mock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Mock dm module before importing any GUI modules
sys.modules['dm'] = mock.MagicMock()
sys.modules['dm.cat_web_service'] = mock.MagicMock()
sys.modules['dm.cat_web_service.api'] = mock.MagicMock()
sys.modules['dm.cat_web_service.api.datasetCatApi'] = mock.MagicMock()
sys.modules['dm.cat_web_service.api.fileCatApi'] = mock.MagicMock()
sys.modules['dm.daq_web_service'] = mock.MagicMock()
sys.modules['dm.daq_web_service.api'] = mock.MagicMock()
sys.modules['dm.daq_web_service.api.experimentDaqApi'] = mock.MagicMock()
sys.modules['dm.ds_web_service'] = mock.MagicMock()
sys.modules['dm.ds_web_service.api'] = mock.MagicMock()
sys.modules['dm.ds_web_service.api.fileDsApi'] = mock.MagicMock()

from PyQt5 import QtWidgets

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_INTEGRITY_DIR = SCRIPT_DIR
OPS_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, DATA_INTEGRITY_DIR)
sys.path.insert(0, os.path.join(OPS_DIR, "disk_monitor"))
sys.path.insert(0, os.path.join(OPS_DIR, "pv_logger"))

import dm_integrity_gui as dig


def _write_config_with_fake_experiments(tmpdir):
    """A config whose local_bases point entirely inside tmpdir, with one
    correctly-named (matches dm_integrity._EXPERIMENT_NAME_RE) experiment
    directory per beamline. Discovery (_discover_and_populate_experiments)
    reads directly from settings.local_bases, NOT from the static
    "experiments" list - a config that omits local_bases would fall back to
    the real ~/mnt/s1c, ~/mnt/s20a mounts and make row counts depend on
    whatever experiments happen to exist on the machine running the test,
    rather than on anything this test controls.
    """
    s1_base = os.path.join(tmpdir, "s1c")
    s20_base = os.path.join(tmpdir, "s20a")
    os.makedirs(os.path.join(s1_base, "test_jan24"))
    os.makedirs(os.path.join(s20_base, "test_jan24"))

    config_path = os.path.join(tmpdir, "config.json")
    config = {
        "settings": {
            "station_name": "SOJOURNER",
            "records_dir": os.path.join(tmpdir, "records"),
            "local_bases": {"s1": s1_base, "s20": s20_base},
            "experiments_per_beamline": 3,
        },
    }
    with open(config_path, "w") as f:
        json.dump(config, f)
    return config_path


def test_data_integrity_panel():
    """Test DataIntegrityPanel standalone."""
    print("Testing DataIntegrityPanel...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = _write_config_with_fake_experiments(tmpdir)

        app = QtWidgets.QApplication([])

        panel = dig.DataIntegrityPanel(config_path, show_font_control=True)
        assert panel.table_widget.rowCount() == 2, "Should have 1 row per beamline (2 total)"

        panel.set_font_size(12)

        app.quit()

    print("✓")


def test_log_updates_label_and_appends_to_console():
    """_log (what every status message now routes through, see
    dm_integrity_gui.py) should update the one-line status label AND
    append a timestamped, non-truncated entry to the scrollable console -
    the label alone can only ever show the latest message, which is what
    made a long SSH failure unreadable before the console was added."""
    print("Testing _log updates both the status label and the console...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = _write_config_with_fake_experiments(tmpdir)
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        panel = dig.DataIntegrityPanel(config_path, show_font_control=False)

        panel.console.clear()
        panel._log("first message")
        panel._log("second message: failed to reach host")

        assert panel.status_label.text() == "second message: failed to reach host", \
            "label should show only the latest message"
        console_text = panel.console.toPlainText()
        assert "first message" in console_text, "console must retain earlier messages, not just the latest"
        assert "second message: failed to reach host" in console_text

        app.quit()

    print("✓")


def test_add_experiment_persists_and_appends_row():
    """"Add experiment..." should append one row without a full rediscovery,
    persist a beamline-tagged entry to the config file (distinct from the
    in-memory-only entries _register_local_root creates for auto-discovered
    rows), and refuse a duplicate name rather than adding a second row."""
    print("Testing add_experiment() persists to config and appends a row...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = _write_config_with_fake_experiments(tmpdir)
        new_root = os.path.join(tmpdir, "manual_exp_root")
        os.makedirs(new_root)

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        panel = dig.DataIntegrityPanel(config_path, show_font_control=False)
        assert panel.table_widget.rowCount() == 2

        class _FakeDialog:
            def __init__(self, parent, beamlines, templates, local_bases=None, known_names=None):
                pass

            def exec_(self):
                return QtWidgets.QDialog.Accepted

            def values(self):
                return "manual_exp", "s1", new_root

        with mock.patch.object(dig, "AddExperimentDialog", _FakeDialog):
            panel.add_experiment()

        assert panel.table_widget.rowCount() == 3, "should have appended exactly one row"
        assert panel._row_for_exp("manual_exp") is not None

        with open(config_path) as f:
            saved = json.load(f)
        manual_entries = [e for e in saved.get("experiments", []) if e.get("name") == "manual_exp"]
        assert len(manual_entries) == 1, "manual experiment should be persisted to the config file"
        assert manual_entries[0]["beamline"] == "s1"
        assert manual_entries[0]["local_root"] == os.path.realpath(new_root)

        # Re-adding the same name must be rejected, not appended again.
        with mock.patch.object(dig, "AddExperimentDialog", _FakeDialog), \
             mock.patch.object(dig, "_message_box") as warn:
            panel.add_experiment()
        assert panel.table_widget.rowCount() == 3, "duplicate add must not append a second row"
        warn.assert_called_once()

        app.quit()

    print("✓")


def test_add_experiment_dialog_browse_autofills_name_and_blocks_duplicates():
    """AddExperimentDialog: picking a folder via Browse should populate the
    experiment name from the folder's basename and infer the beamline from
    which local_base it lives under, and typing a name that's already
    tracked should disable OK rather than waiting until submission."""
    print("Testing AddExperimentDialog browse-autofill and duplicate blocking...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        s1_base = os.path.join(tmpdir, "s1c")
        s20_base = os.path.join(tmpdir, "s20a")
        exp_dir = os.path.join(s20_base, "browsed_exp")
        os.makedirs(exp_dir)

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        dialog = dig.AddExperimentDialog(
            None, ["s1", "s20"], {},
            local_bases={"s1": s1_base, "s20": s20_base},
            known_names={"existing_exp"},
        )

        with mock.patch.object(dig, "_choose_directory", return_value=exp_dir):
            dialog._browse()

        assert dialog.name_edit.text() == "browsed_exp", \
            f"expected name auto-filled from folder basename, got {dialog.name_edit.text()!r}"
        assert dialog.beamline_combo.currentText() == "s20", \
            f"expected beamline inferred from local_bases, got {dialog.beamline_combo.currentText()!r}"
        assert dialog._ok_button.isEnabled(), "OK should be enabled for a non-duplicate name"

        dialog.name_edit.setText("existing_exp")
        assert not dialog._ok_button.isEnabled(), "OK must be disabled once the name matches a known experiment"
        assert dialog.warning_label.text(), "a warning should explain why OK is disabled"

        app.quit()

    print("✓")


def test_stop_checksum_button_swaps_and_calls_systemctl_stop():
    """The combined Verify MD5/Stop button relabels to "Stop" while a
    checksum job is tracked (not just grayed out), and clicking it (after
    confirming) issues `systemctl --user stop <unit>` for that job's real
    unit name rather than just disabling the UI."""
    print("Testing Verify MD5 <-> Stop button relabel and systemctl stop call...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        s1_base = os.path.join(tmpdir, "s1c")
        os.makedirs(os.path.join(s1_base, "test_jan24"))

        config_path = os.path.join(tmpdir, "config.json")
        config = {
            "settings": {
                "station_name": "SOJOURNER",
                "records_dir": os.path.join(tmpdir, "records"),
                "local_bases": {"s1": s1_base},
                "experiments_per_beamline": 3,
                "checksum_hosts": {
                    "s1": {"host": "zion", "user": "s1iduser", "remote_base": "/home/s1iduser/dm_record"}
                },
            },
        }
        with open(config_path, "w") as f:
            json.dump(config, f)

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        panel = dig.DataIntegrityPanel(config_path, show_font_control=False)
        exp_name = "test_jan24"
        assert panel._row_for_exp(exp_name) is not None

        scan_btn, verify_btn = panel._row_buttons[exp_name]
        assert verify_btn.text() == "Verify MD5", "should read Verify MD5 with no job running"

        panel._tracked_checksum_jobs[exp_name] = {"unit_name": "checksum-verify@test_jan24.service", "state": "RUNNING"}
        panel._set_checksum_running_ui(exp_name, True)
        assert verify_btn.text() == "Stop", "should relabel to Stop while a job is tracked"
        assert verify_btn.isEnabled()

        calls = []

        def _fake_run_shell_command(host, user, command, timeout=15):
            calls.append((host, user, command))

        with mock.patch.object(dig.di, "run_shell_command", _fake_run_shell_command), \
             mock.patch.object(dig, "_message_box", return_value=QtWidgets.QMessageBox.Yes):
            panel._on_stop_checksum(exp_name)
            for _ in range(200):
                app.processEvents()
                if exp_name not in panel._checksum_stop_workers:
                    break
                time.sleep(0.01)
            # The worker dict entry is popped by _on_stop_checksum_done as
            # soon as its `done` signal is delivered, but the underlying
            # QThread's own quit()/finished/deleteLater() chain (queued,
            # cross-thread) hasn't necessarily finished by then - give it a
            # few more event-loop passes so the QThread is actually gone
            # before this test (and the process) tears down, same
            # "QThread: Destroyed while thread is still running" hazard
            # test_disk_monitor_gui.py already documents and works around.
            app.processEvents()
            time.sleep(0.05)
            app.processEvents()

        assert exp_name not in panel._checksum_stop_workers, "stop worker should have finished"
        assert len(calls) == 1, f"expected exactly one systemctl call, got {calls}"
        host, user, command = calls[0]
        assert host == "zion" and user == "s1iduser"
        assert "systemctl" in command and "stop" in command and "checksum-verify@test_jan24.service" in command

        # Simulate the poll tick discovering the CANCELLED status
        # checksum_worker.py's own SIGTERM handler would have written.
        panel._set_checksum_running_ui(exp_name, False)
        assert verify_btn.text() == "Verify MD5"

        app.quit()

    print("✓")


def test_remove_experiment_only_offered_for_manual_rows():
    """Only manually-added rows get a Remove button; removing one deletes
    its row and its beamline-tagged config entry, without touching
    auto-discovered rows or their in-memory-only local_root entries."""
    print("Testing Remove is manual-only and persists the deletion...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        s1_base = os.path.join(tmpdir, "s1c")
        os.makedirs(os.path.join(s1_base, "auto_jan24"))
        manual_root = os.path.join(tmpdir, "manual_root")
        os.makedirs(manual_root)

        config_path = os.path.join(tmpdir, "config.json")
        config = {
            "settings": {
                "station_name": "SOJOURNER",
                "records_dir": os.path.join(tmpdir, "records"),
                "local_bases": {"s1": s1_base},
                "experiments_per_beamline": 3,
            },
            "experiments": [
                {"name": "manual_exp", "beamline": "s1", "local_root": manual_root, "dataset": None}
            ],
        }
        with open(config_path, "w") as f:
            json.dump(config, f)

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        panel = dig.DataIntegrityPanel(config_path, show_font_control=False)

        assert panel._row_for_exp("auto_jan24") is not None
        assert panel._row_for_exp("manual_exp") is not None

        auto_row = panel._row_for_exp("auto_jan24")
        manual_row = panel._row_for_exp("manual_exp")
        # +1 in each count is the trailing addStretch() layout item (a
        # QSpacerItem, not a button) that keeps button sizes consistent
        # across rows regardless of label width - see _populate_experiment_row.
        # Scan + the combined Verify MD5/Stop button + the history-summary
        # label = 3 widgets normally.
        assert panel.table_widget.cellWidget(auto_row, 4).layout().count() == 3 + 1, \
            "auto-discovered row should have Scan + Verify MD5/Stop + history label only, no Remove"
        assert panel.table_widget.cellWidget(manual_row, 4).layout().count() == 4 + 1, \
            "manually-added row should have an extra Remove button"

        with mock.patch.object(dig, "_message_box", return_value=QtWidgets.QMessageBox.Yes):
            panel._on_remove_experiment("manual_exp")

        assert panel._row_for_exp("manual_exp") is None, "removed row should be gone from the table"
        assert panel._row_for_exp("auto_jan24") is not None, "unrelated row must be untouched"

        with open(config_path) as f:
            saved = json.load(f)
        assert not any(e.get("name") == "manual_exp" for e in saved.get("experiments", [])), \
            "removed experiment must no longer be persisted to disk"

        app.quit()

    print("✓")


def test_history_summary_indicator_populates_and_refreshes():
    """The compact "N recs" label next to Scan/Verify MD5 should be empty
    with no saved records, then show a count + tooltip once a record
    exists - populated at row-creation time and refreshed the moment a
    fresh report is painted (_paint_experiment_row), not just on restart."""
    print("Testing history summary indicator populates and refreshes...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        s1_base = os.path.join(tmpdir, "s1c")
        os.makedirs(os.path.join(s1_base, "test_jan24"))
        records_dir = os.path.join(tmpdir, "records")

        config_path = os.path.join(tmpdir, "config.json")
        config = {
            "settings": {
                "station_name": "SOJOURNER",
                "records_dir": records_dir,
                "local_bases": {"s1": s1_base},
                "experiments_per_beamline": 3,
            },
        }
        with open(config_path, "w") as f:
            json.dump(config, f)

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        panel = dig.DataIntegrityPanel(config_path, show_font_control=False)
        exp_name = "test_jan24"

        label = panel._row_history_labels[exp_name]
        assert label.text() == "", "no saved records yet - indicator should be empty"

        comparison = {"a.h5": "MATCH", "b.h5": "LOCAL_ONLY"}
        report = dig.di.build_report(exp_name, {"upload_complete": False}, comparison)
        dig.di.save_record(records_dir, exp_name, report)

        row = panel._row_for_exp(exp_name)
        panel._paint_experiment_row(row, report)

        assert label.text() == "1 rec", f"expected '1 rec' after one saved record, got {label.text()!r}"
        assert "1 saved record" in label.toolTip()
        assert "good" in label.toolTip() and "bad" in label.toolTip()

        app.quit()

    print("✓")


def test_history_detail_dialog_lists_problem_files():
    """HistoryDetailDialog should surface which specific files are missing/
    mismatched, not just a good/bad count - the detail the old plain
    QMessageBox history view never showed."""
    print("Testing HistoryDetailDialog surfaces per-file problem detail...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        records_dir = os.path.join(tmpdir, "records")
        exp_name = "test_jan24"

        comparison = {
            "good.h5": "MATCH",
            "corrupted.h5": "CHECKSUM_MISMATCH",  # comparison-level MATCH but checksum failed below
            "missing_locally.h5": "REMOTE_ONLY",
            "not_uploaded.h5": "LOCAL_ONLY",
            "resized.h5": "SIZE_MISMATCH",
        }
        checksum_results = {
            "good.h5": "CHECKSUM_MATCH",
            "corrupted.h5": "CHECKSUM_MISMATCH",
        }
        report = dig.di.build_report(exp_name, {"upload_complete": False}, comparison, checksum_results)
        dig.di.save_record(records_dir, exp_name, report)

        records = dig.di.list_records(records_dir, exp_name)
        assert records, "fixture record should be found by list_records"

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        dialog = dig.HistoryDetailDialog(None, exp_name, records)

        problem_paths = set()
        for row in range(dialog.table.rowCount()):
            problem_paths.add(dialog.table.item(row, 0).text())

        assert "missing_locally.h5" in problem_paths
        assert "not_uploaded.h5" in problem_paths
        assert "resized.h5" in problem_paths
        assert "corrupted.h5" in problem_paths
        assert "good.h5" not in problem_paths, "a fully-matched file should not be listed as a problem"
        assert dialog.summary_label.text(), "summary should be populated"

        app.quit()

    print("✓")


def test_data_integrity_window():
    """Test DataIntegrityWindow standalone."""
    print("Testing DataIntegrityWindow...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = _write_config_with_fake_experiments(tmpdir)

        app = QtWidgets.QApplication([])

        window = dig.DataIntegrityWindow(config_path)
        window.set_font_size(14)

        app.quit()

    print("✓")


if __name__ == "__main__":
    try:
        test_data_integrity_panel()
        test_log_updates_label_and_appends_to_console()
        test_add_experiment_persists_and_appends_row()
        test_add_experiment_dialog_browse_autofills_name_and_blocks_duplicates()
        test_stop_checksum_button_swaps_and_calls_systemctl_stop()
        test_remove_experiment_only_offered_for_manual_rows()
        test_history_summary_indicator_populates_and_refreshes()
        test_history_detail_dialog_lists_problem_files()
        test_data_integrity_window()
        print("\nGUI smoke tests passed! ✓")
    except Exception as e:
        print(f"\nGUI test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
