#!/usr/bin/env python3
"""
Offscreen smoke test for dm_integrity_gui standalone and in combined ops_gui.
"""

import json
import os
import sys
import tempfile
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
        test_history_detail_dialog_lists_problem_files()
        test_data_integrity_window()
        print("\nGUI smoke tests passed! ✓")
    except Exception as e:
        print(f"\nGUI test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
