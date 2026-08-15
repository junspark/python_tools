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


def test_data_integrity_panel():
    """Test DataIntegrityPanel standalone."""
    print("Testing DataIntegrityPanel...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        config = {
            "settings": {
                "station_name": "SOJOURNER",
                "records_dir": os.path.join(tmpdir, "records")
            },
            "experiments": [
                {
                    "name": "exp1",
                    "local_root": tmpdir,
                    "dataset": None,
                    "running": True
                },
                {
                    "name": "exp2",
                    "local_root": tmpdir,
                    "dataset": None,
                    "running": False
                }
            ]
        }

        with open(config_path, "w") as f:
            json.dump(config, f)

        app = QtWidgets.QApplication([])

        panel = dig.DataIntegrityPanel(config_path, show_font_control=True)
        assert panel.table_widget.rowCount() == 2, "Should have 2 experiment rows"

        panel.set_font_size(12)

        app.quit()

    print("✓")


def test_data_integrity_window():
    """Test DataIntegrityWindow standalone."""
    print("Testing DataIntegrityWindow...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        config = {
            "settings": {
                "station_name": "SOJOURNER",
                "records_dir": os.path.join(tmpdir, "records")
            },
            "experiments": [
                {
                    "name": "exp1",
                    "local_root": tmpdir,
                    "dataset": None,
                    "running": False
                }
            ]
        }

        with open(config_path, "w") as f:
            json.dump(config, f)

        app = QtWidgets.QApplication([])

        window = dig.DataIntegrityWindow(config_path)
        window.set_font_size(14)

        app.quit()

    print("✓")


if __name__ == "__main__":
    try:
        test_data_integrity_panel()
        test_data_integrity_window()
        print("\nGUI smoke tests passed! ✓")
    except Exception as e:
        print(f"\nGUI test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
