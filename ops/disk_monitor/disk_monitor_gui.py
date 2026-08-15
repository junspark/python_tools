#!/usr/bin/env python3
"""
Disk-space monitor GUI (PyQt5).

Reads/writes the same JSON config as disk_monitor.py and reuses all of its
sampling, rate, and alert logic - this file only adds the display and
editing layer.

Usage
-----
  python disk_monitor_gui.py
  python disk_monitor_gui.py --config /path/to/disk_monitor_config.json
"""

import argparse
import os
import subprocess
import sys
import time

import disk_monitor as dm

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    sys.exit(
        "PyQt5 is required for the GUI but is not installed.\n"
        "Install it with:  pip install PyQt5\n"
        "(disk_monitor.py's 'check'/'monitor' CLI subcommands work without it.)"
    )

COLUMNS = ["Name", "Path", "Used %", "Free (GB)", "Rate (GB/hr)", "ETA (days)", "Threshold %", "Status"]

DEFAULT_FONT_SIZE = 10

LEVEL_COLORS = {
    "ok": QtGui.QColor("#c8f7c5"),
    "warn": QtGui.QColor("#fff3b0"),
    "alert": QtGui.QColor("#f7c5c5"),
    "error": QtGui.QColor("#e0e0e0"),
}


def _cron_status(script_path):
    """
    Best-effort, read-only check of whether crond looks alive and a job
    referencing this script is scheduled. Never raises - crontab/systemctl
    may not exist or be readable on every host.
    """
    service_active = None
    for svc in ("crond", "cron"):
        try:
            out = subprocess.run(["systemctl", "is-active", svc],
                                  capture_output=True, text=True, timeout=5)
        except Exception:
            continue
        state = out.stdout.strip()
        if state == "active":
            service_active = True
            break
        if state in ("inactive", "failed"):
            service_active = False

    job_scheduled = None
    try:
        out = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            job_scheduled = os.path.basename(script_path) in out.stdout
    except Exception:
        pass

    if service_active is False:
        return "Cron: SERVICE DOWN"
    if job_scheduled is False:
        return "Cron: not scheduled"
    if service_active and job_scheduled:
        return "Cron: OK"
    return "Cron: unknown"


class AddTargetDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add monitored path")

        self.name_edit = QtWidgets.QLineEdit()
        self.path_edit = QtWidgets.QLineEdit()
        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)

        self.warn_spin = QtWidgets.QSpinBox()
        self.warn_spin.setRange(1, 100)
        self.warn_spin.setValue(85)

        self.threshold_spin = QtWidgets.QSpinBox()
        self.threshold_spin.setRange(1, 100)
        self.threshold_spin.setValue(95)

        path_row = QtWidgets.QHBoxLayout()
        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse_btn)

        form = QtWidgets.QFormLayout()
        form.addRow("Name:", self.name_edit)
        form.addRow("Path:", path_row)
        form.addRow("Warn %:", self.warn_spin)
        form.addRow("Alert threshold %:", self.threshold_spin)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select directory")
        if path:
            self.path_edit.setText(path)

    def target(self):
        return {
            "name": self.name_edit.text().strip(),
            "path": self.path_edit.text().strip(),
            "warn_pct": self.warn_spin.value(),
            "threshold_pct": self.threshold_spin.value(),
        }


class DiskMonitorPanel(QtWidgets.QWidget):
    """
    All disk-monitor GUI behavior, as a plain QWidget rather than a
    QMainWindow, so it can be embedded as a tab in ops_gui.py as well as
    hosted standalone by DiskMonitorWindow below.
    """

    def __init__(self, config_path, parent=None, show_font_control=True):
        super().__init__(parent)
        self.config_path = config_path
        self.cfg = dm.load_config(config_path)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QtWidgets.QToolBar()
        layout.addWidget(toolbar)

        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        self.status_bar = QtWidgets.QStatusBar()
        layout.addWidget(self.status_bar)

        toolbar.addAction("Refresh now", self.refresh)
        toolbar.addAction("Add path...", self.add_path)
        toolbar.addAction("Remove selected", self.remove_selected)
        toolbar.addAction("Edit recipients...", self.edit_recipients)
        toolbar.addAction("Send test email", self.send_test_email)

        toolbar.addSeparator()
        self.cron_label = QtWidgets.QLabel(" Cron: checking... ")
        toolbar.addWidget(self.cron_label)

        toolbar.addSeparator()
        toolbar.addWidget(QtWidgets.QLabel(" Rate avg (min): "))
        self.rate_window_spin = QtWidgets.QSpinBox()
        self.rate_window_spin.setRange(1, 240)
        self.rate_window_spin.setValue(int(self.cfg["settings"]["rate_window_min"]))
        self.rate_window_spin.valueChanged.connect(self.set_rate_window)
        toolbar.addWidget(self.rate_window_spin)

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
        self.timer.timeout.connect(self.refresh)
        self.timer.start(int(self.cfg["settings"]["check_interval_sec"] * 1000))

        self.refresh()

    def refresh(self):
        settings = self.cfg["settings"]
        now = time.time()

        # Snapshot the most recent recorded sample per target *before* this
        # cycle's own check_targets() call appends a fresh one. A large gap
        # here means nothing wrote to history since then - e.g. the cron job
        # (or this GUI) wasn't actually running while this window was closed.
        last_seen = {}
        for entry in dm._read_history(settings["history_file"]):
            last_seen[entry["name"]] = max(last_seen.get(entry["name"], 0), entry["ts"])

        statuses = dm.check_targets(self.cfg, now=now)
        sent = dm.process_alerts(self.cfg, statuses)

        stale_gap_sec = 2 * settings["check_interval_sec"]
        stale = []
        for target in self.cfg["targets"]:
            prior_ts = last_seen.get(target["name"])
            if prior_ts is not None and (now - prior_ts) > stale_gap_sec:
                stale.append((target["name"], now - prior_ts))

        self.cron_label.setText(" {} ".format(_cron_status(
            os.path.join(dm.SCRIPT_DIR, "disk_monitor.py"))))

        self.table.setRowCount(len(statuses))
        for row, s in enumerate(statuses):
            if s.get("level") == "error":
                values = [s["name"], s["path"], "-", "-", "-", "-", "-", "ERROR: " + s["error"]]
            else:
                eta = "{:.1f}".format(s["eta_days"]) if s["eta_days"] is not None else "-"
                values = [
                    s["name"], s["path"],
                    "{:.1f}".format(s["percent"]),
                    "{:.1f}".format(s["free"] / dm.GB),
                    "{:.2f}".format(s["rate_bytes_per_day"] / 24 / dm.GB),
                    eta,
                    str(s["threshold_pct"]),
                    s["level"].upper(),
                ]

            color = LEVEL_COLORS.get(s.get("level"), LEVEL_COLORS["error"])
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setBackground(color)
                self.table.setItem(row, col, item)

        now_str = QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.TextDate)
        msg = "Last checked: {}".format(now_str)
        if sent:
            msg += "  |  Alert email sent for: {}".format(", ".join(sent))
        if stale:
            gaps = ", ".join("{} ({:.0f} min)".format(n, g / 60) for n, g in stale)
            msg += "  |  ⚠ monitoring gap detected: {}".format(gaps)
        self.status_bar.showMessage(msg)

    def set_rate_window(self, minutes):
        self.cfg["settings"]["rate_window_min"] = minutes
        dm.save_config(self.cfg, self.config_path)
        self.refresh()

    def set_font_size(self, size):
        font = QtWidgets.QApplication.instance().font()
        font.setPointSize(size)
        QtWidgets.QApplication.instance().setFont(font)
        self.table.setFont(font)
        self.table.horizontalHeader().setFont(font)
        self.table.resizeRowsToContents()
        for toolbar in self.findChildren(QtWidgets.QToolBar):
            toolbar.setFont(font)
            for widget in toolbar.findChildren(QtWidgets.QWidget):
                widget.setFont(font)

    def add_path(self):
        dialog = AddTargetDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        target = dialog.target()
        if not target["name"] or not target["path"]:
            QtWidgets.QMessageBox.warning(self, "Missing fields", "Name and path are required.")
            return

        self.cfg["targets"].append(target)
        dm.save_config(self.cfg, self.config_path)
        self.refresh()

    def edit_recipients(self):
        current = ", ".join(self.cfg["settings"].get("recipients", []))
        text, ok = QtWidgets.QInputDialog.getText(
            self, "Alert recipients", "Comma-separated email addresses:",
            QtWidgets.QLineEdit.Normal, current)
        if not ok:
            return
        self.cfg["settings"]["recipients"] = [addr.strip() for addr in text.split(",") if addr.strip()]
        dm.save_config(self.cfg, self.config_path)
        self.refresh()

    def remove_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for row in rows:
            del self.cfg["targets"][row]
        dm.save_config(self.cfg, self.config_path)
        self.refresh()

    def send_test_email(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        statuses = dm.check_targets(self.cfg)
        valid = [s for s in statuses if s.get("level") != "error"]
        if not valid:
            QtWidgets.QMessageBox.warning(self, "No targets", "No valid targets to test.")
            return

        status = dict(valid[rows[0]] if rows else valid[0])
        status["level"] = "alert"
        ok = dm.send_alert_email(self.cfg, status, all_statuses=valid)
        if ok:
            QtWidgets.QMessageBox.information(self, "Test email", "Test alert sent (or printed to console).")
        else:
            QtWidgets.QMessageBox.critical(self, "Test email failed", "Failed to send test email; see console.")


class DiskMonitorWindow(QtWidgets.QMainWindow):
    """Standalone window hosting DiskMonitorPanel - used when this file is
    run directly rather than embedded as a tab in ops_gui.py."""

    def __init__(self, config_path):
        super().__init__()
        self.setWindowTitle("Disk Space Monitor")
        self.resize(900, 400)
        self.panel = DiskMonitorPanel(config_path)
        self.setCentralWidget(self.panel)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Disk-space monitor GUI")
    parser.add_argument("--config", default=dm.DEFAULT_CONFIG_PATH, help="Path to config JSON")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = DiskMonitorWindow(args.config)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
