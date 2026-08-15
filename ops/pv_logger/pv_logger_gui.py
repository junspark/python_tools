#!/usr/bin/env python3
"""
PV logger GUI (PyQt5).

Not a live table of every monitored PV - with ~500+ entries in the master
list that isn't useful to stare at. Instead: a status panel (is monitoring
running, since when, which output file, how many PVs came online at
discovery) plus a table of only the PVs that are *currently offline*, so a
dropped device is the thing that actually draws your eye.

Usage
-----
  python pv_logger_gui.py
  python pv_logger_gui.py --config /path/to/pv_master_list.json
"""

import argparse
import os
import sys
import time

import pv_logger as pl

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    sys.exit(
        "PyQt5 is required for the GUI but is not installed.\n"
        "Install it with:  pip install PyQt5\n"
        "(pv_logger.py's 'list-pvs'/'start' CLI subcommands work without it.)"
    )

OFFLINE_COLUMNS = ["Name", "PV"]

DEFAULT_FONT_SIZE = 10

STATUS_COLORS = {
    "running": "#c8f7c5",
    "stopped": "#e0e0e0",
}


class StartExperimentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, default_dir="", devices=None):
        super().__init__(parent)
        self.setWindowTitle("Start new experiment")

        self.outfile_edit = QtWidgets.QLineEdit()
        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        self._default_dir = default_dir

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.outfile_edit)
        row.addWidget(browse_btn)

        form = QtWidgets.QFormLayout()
        form.addRow("Output CSV:", row)

        # Device checklist
        self.device_checks = {}
        if devices:
            device_group = QtWidgets.QGroupBox("Select devices to monitor:")
            device_layout = QtWidgets.QVBoxLayout()

            for device in devices:
                checkbox = QtWidgets.QCheckBox(device)
                checkbox.setChecked(True)  # All checked by default
                self.device_checks[device] = checkbox
                device_layout.addWidget(checkbox)

            device_scroll = QtWidgets.QScrollArea()
            device_scroll.setWidgetResizable(True)
            device_widget = QtWidgets.QWidget()
            device_widget.setLayout(device_layout)
            device_scroll.setWidget(device_widget)
            device_scroll.setMaximumHeight(150)

            device_group.setLayout(QtWidgets.QVBoxLayout())
            device_group.layout().addWidget(device_scroll)
            form.addRow(device_group)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Output CSV", self._default_dir, "CSV files (*.csv)")
        if path:
            self.outfile_edit.setText(path)

    def outfile(self):
        return self.outfile_edit.text().strip()

    def selected_devices(self):
        """Return list of checked device names."""
        return [device for device, checkbox in self.device_checks.items()
                if checkbox.isChecked()]


class PVLoggerPanel(QtWidgets.QWidget):
    """
    All PV-logger GUI behavior, as a plain QWidget rather than a
    QMainWindow, so it can be embedded as a tab in ops_gui.py as well as
    hosted standalone by PVLoggerWindow below.
    """

    def __init__(self, config_path, parent=None, show_font_control=True):
        super().__init__(parent)
        self.config_path = config_path
        self.base_config_dir = os.path.dirname(config_path)
        self.cfg = pl.load_config(config_path)

        self.online = {}
        self.offline_at_start = []
        self.outfile = None
        self.start_time = None
        self.running = False
        self.current_beamline = "s1"

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QtWidgets.QToolBar()
        layout.addWidget(toolbar)

        # Beamline selector
        toolbar.addWidget(QtWidgets.QLabel(" Beamline: "))
        self.beamline_combo = QtWidgets.QComboBox()
        self.beamline_combo.addItems(["s1", "s20"])
        self.beamline_combo.currentTextChanged.connect(self._on_beamline_changed)
        toolbar.addWidget(self.beamline_combo)
        toolbar.addSeparator()

        self.status_label = QtWidgets.QLabel("STOPPED")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setAutoFillBackground(True)
        self._paint_status(running=False)
        layout.addWidget(self.status_label)

        self.info_label = QtWidgets.QLabel("No experiment started yet.")
        layout.addWidget(self.info_label)

        layout.addWidget(QtWidgets.QLabel("Currently offline:"))
        self.offline_table = QtWidgets.QTableWidget(0, len(OFFLINE_COLUMNS))
        self.offline_table.setHorizontalHeaderLabels(OFFLINE_COLUMNS)
        self.offline_table.horizontalHeader().setStretchLastSection(True)
        self.offline_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.offline_table)

        self.status_bar = QtWidgets.QStatusBar()
        layout.addWidget(self.status_bar)

        toolbar.addAction("Start new experiment...", self.start_experiment)
        self.stop_action = toolbar.addAction("Stop", self.stop_monitoring)
        self.stop_action.setEnabled(False)
        toolbar.addAction("Edit recipients...", self.edit_recipients)

        if show_font_control:
            toolbar.addSeparator()
            toolbar.addWidget(QtWidgets.QLabel(" Font size: "))
            self.font_size_spin = QtWidgets.QSpinBox()
            self.font_size_spin.setRange(6, 24)
            self.font_size_spin.setValue(DEFAULT_FONT_SIZE)
            self.font_size_spin.valueChanged.connect(self.set_font_size)
            toolbar.addWidget(self.font_size_spin)

        self.set_font_size(DEFAULT_FONT_SIZE)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)

    def _on_beamline_changed(self, beamline_name):
        """Load config for selected beamline."""
        if self.running:
            QtWidgets.QMessageBox.warning(self, "Monitoring active",
                                         "Cannot switch beamlines while monitoring is running.")
            self.beamline_combo.blockSignals(True)
            self.beamline_combo.setCurrentText(self.current_beamline)
            self.beamline_combo.blockSignals(False)
            return

        self.current_beamline = beamline_name

        # Try to load beamline-specific config
        config_file = os.path.join(self.base_config_dir, f"pv_master_list_{beamline_name}.json")

        if os.path.exists(config_file):
            try:
                self.cfg = pl.load_config(config_file)
                self.status_bar.showMessage(f"Switched to {beamline_name}")
            except Exception as e:
                self.status_bar.showMessage(f"Error loading {beamline_name} config: {str(e)}")
                self.cfg = pl.load_config(self.config_path)
        else:
            # Fallback to default config if beamline-specific one doesn't exist
            self.cfg = pl.load_config(self.config_path)
            self.status_bar.showMessage(f"Using default PV list for {beamline_name}")

    def _paint_status(self, running):
        text = "RUNNING" if running else "STOPPED"
        color = STATUS_COLORS["running"] if running else STATUS_COLORS["stopped"]
        self.status_label.setText(text)
        palette = self.status_label.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(color))
        self.status_label.setPalette(palette)

    def start_experiment(self):
        # Load config and get all available devices
        self.cfg = pl.load_config(self.config_path)
        all_devices = pl.get_all_devices(self.cfg["pvs"])

        # Show dialog with device checklist
        dialog = StartExperimentDialog(self, devices=all_devices)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        outfile = dialog.outfile()
        if not outfile:
            QtWidgets.QMessageBox.warning(self, "Missing output file", "Choose an output CSV path.")
            return

        selected_devices = dialog.selected_devices()
        if not selected_devices:
            QtWidgets.QMessageBox.warning(self, "No devices selected", "Select at least one device to monitor.")
            return

        # Filter PVs to only those in selected devices
        filtered_pvs = pl.filter_pvs_by_devices(self.cfg["pvs"], selected_devices)
        self.status_bar.showMessage(f"Discovering PVs in {len(selected_devices)} device(s)...")
        QtWidgets.QApplication.processEvents()

        online, offline = pl.discover_pvs(filtered_pvs, self.cfg["settings"]["connect_timeout_sec"])
        if not online:
            QtWidgets.QMessageBox.critical(self, "No PVs online", "No PVs from selected devices are online.")
            self.status_bar.showMessage("Discovery found 0 PVs online.")
            return

        names = sorted(online)
        pl.write_header(outfile, names, device_selection=selected_devices)
        skipped_path = pl.write_skipped_report(outfile, offline) if offline else None

        self.online = online
        self.offline_at_start = offline
        self.outfile = outfile
        self.start_time = time.time()
        self.running = True

        self._paint_status(running=True)
        self.info_label.setText(
            "{} of {} PVs online (from {} devices)  |  Output: {}".format(
                len(online), len(online) + len(offline), len(selected_devices), outfile))
        msg = "Started at {}".format(time.ctime(self.start_time))
        if skipped_path:
            msg += "  |  Offline-at-start list: {}".format(skipped_path)
        self.status_bar.showMessage(msg)

        self.offline_table.setRowCount(0)
        self.stop_action.setEnabled(True)

        self.timer.start(int(self.cfg["settings"]["log_interval_sec"] * 1000))
        self.tick()

    def stop_monitoring(self):
        self.timer.stop()
        self.running = False
        self._paint_status(running=False)
        self.stop_action.setEnabled(False)
        self.status_bar.showMessage("Stopped at {}".format(time.ctime()))

    def tick(self):
        if not self.online:
            return

        now = time.time()
        values, currently_offline = pl.sample(self.online)
        pl.write_row(self.outfile, sorted(self.online), values, now)
        dropped = pl.process_drop_alerts(self.cfg, currently_offline, self.outfile)

        self.offline_table.setRowCount(len(currently_offline))
        pv_by_name = {name: pv_obj.pvname for name, pv_obj in self.online.items()}
        for row, name in enumerate(sorted(currently_offline)):
            self.offline_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.offline_table.setItem(row, 1, QtWidgets.QTableWidgetItem(pv_by_name.get(name, "")))

        msg = "Last write: {}".format(time.ctime(now))
        if dropped:
            msg += "  |  Alert email sent for: {}".format(", ".join(dropped))
        self.status_bar.showMessage(msg)

    def set_font_size(self, size):
        font = QtWidgets.QApplication.instance().font()
        font.setPointSize(size)
        QtWidgets.QApplication.instance().setFont(font)
        self.offline_table.setFont(font)
        self.offline_table.horizontalHeader().setFont(font)
        self.offline_table.resizeRowsToContents()
        for toolbar in self.findChildren(QtWidgets.QToolBar):
            toolbar.setFont(font)
            for widget in toolbar.findChildren(QtWidgets.QWidget):
                widget.setFont(font)

    def edit_recipients(self):
        current = ", ".join(self.cfg["settings"].get("recipients", []))
        text, ok = QtWidgets.QInputDialog.getText(
            self, "Alert recipients", "Comma-separated email addresses:",
            QtWidgets.QLineEdit.Normal, current)
        if not ok:
            return
        self.cfg["settings"]["recipients"] = [addr.strip() for addr in text.split(",") if addr.strip()]
        pl.save_config(self.cfg, self.config_path)


class PVLoggerWindow(QtWidgets.QMainWindow):
    """Standalone window hosting PVLoggerPanel - used when this file is run
    directly rather than embedded as a tab in ops_gui.py."""

    def __init__(self, config_path):
        super().__init__()
        self.setWindowTitle("PV Logger")
        self.resize(700, 400)
        self.panel = PVLoggerPanel(config_path)
        self.setCentralWidget(self.panel)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="PV logger GUI")
    parser.add_argument("--config", default=pl.DEFAULT_CONFIG_PATH, help="Path to master PV list JSON")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = PVLoggerWindow(args.config)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
