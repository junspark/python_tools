#!/usr/bin/env python3
"""
Combined ops GUI: disk-space monitor, PV logger, and data integrity as tabs in one window.

Each tab is the same panel used by that tool's standalone GUI
(disk_monitor/disk_monitor_gui.py, pv_logger/pv_logger_gui.py,
data_integrity/dm_integrity_gui.py) - no logic is duplicated here, this file
only assembles them into one QTabWidget.

Usage
-----
  python ops_gui.py
  python ops_gui.py --disk-config /path/to/disk_monitor_config.json \\
                     --pv-config /path/to/pv_master_list.json \\
                     --di-config /path/to/data_integrity_config.json
"""

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "disk_monitor"))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "pv_logger"))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "data_integrity"))

import disk_monitor_gui as dmg
import pv_logger_gui as plg
import dm_integrity_gui as dig

try:
    from PyQt5 import QtWidgets
except ImportError:
    sys.exit(
        "PyQt5 is required for the GUI but is not installed.\n"
        "Install it with:  pip install PyQt5\n"
    )


DEFAULT_FONT_SIZE = 10


class OpsGuiWindow(QtWidgets.QMainWindow):
    def __init__(self, disk_config, pv_config, di_config):
        super().__init__()
        self.setWindowTitle("Ops")
        self.resize(1000, 500)

        # Each panel normally has its own "Font size" control; suppress
        # all and drive them from one control here instead, so there's a
        # single font size for the whole window rather than one per tab.
        self.disk_panel = dmg.DiskMonitorPanel(disk_config, show_font_control=False)
        self.pv_panel = plg.PVLoggerPanel(pv_config, show_font_control=False)
        self.di_panel = dig.DataIntegrityPanel(di_config, show_font_control=False)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.disk_panel, "Disk Space")
        tabs.addTab(self.pv_panel, "PV Logger")
        tabs.addTab(self.di_panel, "Data Integrity")
        self.setCentralWidget(tabs)

        toolbar = self.addToolBar("View")
        toolbar.addWidget(QtWidgets.QLabel(" Font size: "))
        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(6, 24)
        self.font_size_spin.setValue(DEFAULT_FONT_SIZE)
        self.font_size_spin.valueChanged.connect(self.set_font_size)
        toolbar.addWidget(self.font_size_spin)

        self.set_font_size(DEFAULT_FONT_SIZE)

    def set_font_size(self, size):
        self.disk_panel.set_font_size(size)
        self.pv_panel.set_font_size(size)
        self.di_panel.set_font_size(size)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Combined ops GUI (disk monitor + PV logger + data integrity)")
    parser.add_argument("--disk-config", default=dmg.dm.DEFAULT_CONFIG_PATH,
                         help="Path to disk_monitor config JSON")
    parser.add_argument("--pv-config", default=plg.pl.DEFAULT_CONFIG_PATH,
                         help="Path to pv_logger master list JSON")
    di_config_default = os.path.join(SCRIPT_DIR, "data_integrity", "data_integrity_config.json")
    parser.add_argument("--di-config", default=di_config_default,
                         help="Path to data_integrity config JSON")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = OpsGuiWindow(args.disk_config, args.pv_config, args.di_config)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
