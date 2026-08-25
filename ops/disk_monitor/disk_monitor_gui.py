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


def _center_on_parent(dialog, parent):
    """Explicitly position dialog over parent's current on-screen geometry
    before it's shown, rather than trusting the window manager/compositor's
    default placement for a new top-level window - confirmed necessary on
    at least one real deployment: a Wayland/Mutter compositor with an
    unusual multi-monitor layout placed brand-new, position-less windows
    entirely off every monitor. An explicit move() issued after a window
    is already mapped gets silently overridden by that same compositor,
    but a position requested before the window is first shown is honored.
    No-op if parent isn't currently visible - nothing sensible to center on
    yet."""
    if parent is None or not parent.isVisible():
        return
    # adjustSize() first, but ONLY for a dialog that never explicitly
    # resize()d itself (e.g. AddTargetDialog, sized purely by its layout) -
    # it otherwise still reports a placeholder width/height at this point.
    # WA_Resized is set automatically by resize() (Qt's own way of
    # tracking "has this widget been given an explicit size"), so this
    # skips adjustSize() for a dialog like TopFoldersDialog that
    # deliberately resized itself larger than its layout's natural
    # minimum - calling adjustSize() there would shrink it back down.
    if not dialog.testAttribute(QtCore.Qt.WA_Resized):
        dialog.adjustSize()
    parent_geo = parent.window().frameGeometry()
    x = parent_geo.center().x() - dialog.width() // 2
    y = parent_geo.center().y() - dialog.height() // 2
    # Clamp the WHOLE rectangle inside whichever screen the parent window
    # is actually on - not just floor negative coordinates. Confirmed
    # directly not enough on a real unusual multi-monitor layout (mixed
    # sizes/offsets): centering on parent_geo's center point can still
    # place a dialog's edges past that monitor's actual bounds even though
    # the center point itself looks reasonable, landing it partly or
    # entirely on/past a neighboring monitor with a different origin.
    # screenAt(parent_geo.center()) - not primaryScreen() - because the
    # window actually being centered on may not be on the primary screen
    # at all in a multi-monitor setup.
    screen = QtWidgets.QApplication.screenAt(parent_geo.center()) or QtWidgets.QApplication.primaryScreen()
    if screen is not None:
        avail = screen.availableGeometry()
        x = max(avail.x(), min(x, avail.x() + avail.width() - dialog.width()))
        y = max(avail.y(), min(y, avail.y() + avail.height() - dialog.height()))
    else:
        x, y = max(0, x), max(0, y)
    dialog.move(x, y)
    # WindowStaysOnTopHint - set before the show() below, not after:
    # confirmed directly that even a completely unrelated, bare Xlib app
    # (xterm, no Qt/GTK involved) is unreliably mapped/focused on this
    # remote X11-forwarding setup, while a modern GTK app (gedit) shows up
    # every time - a window-manager/focus-stealing-prevention heuristic
    # neither plain Xlib nor Qt's xcb backend satisfies the way GTK's
    # does, not a bug specific to any one dialog here. Staying-on-top
    # bypasses that heuristic entirely rather than politely requesting
    # around it via raise_()/activateWindow() alone, which were not
    # sufficient on their own.
    dialog.setWindowFlags(dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    # show()/raise_()/activateWindow() here, not left to the caller's
    # later exec_(): plain show()/exec_() can map a window at a perfectly
    # valid, on-screen position on this display setup without ever
    # bringing it to the front - no error, no crash, the dialog is simply
    # invisible until manually found. exec_() on an already-shown widget
    # is fine (it just switches on modality and starts the local event
    # loop), so doing the actual mapping here - right after positioning,
    # before the caller's exec_() call - is what lets raise_()/
    # activateWindow() apply to a window that actually exists yet, rather
    # than being no-ops against a window that isn't mapped until exec_()
    # gets to it.
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()


def _message_box(icon, parent, title, text, buttons=QtWidgets.QMessageBox.Ok, default_button=None):
    """Drop-in replacement for QtWidgets.QMessageBox.information/warning/
    critical/question's static convenience methods, with the same
    explicit-positioning fix _center_on_parent applies to every custom
    QDialog here - those static methods build and exec_ their own
    QMessageBox internally with no hook to position it first, so on the
    same Wayland/Mutter setup _center_on_parent exists for, a plain
    QMessageBox.information() call is just as invisible as an unpositioned
    QDialog would be (confirmed directly in data_integrity's dm_integrity_gui.py -
    see its own _message_box)."""
    box = QtWidgets.QMessageBox(icon, title, text, buttons, parent)
    if default_button is not None:
        box.setDefaultButton(default_button)
    _center_on_parent(box, parent)
    return box.exec_()


def _choose_directory(parent, title, start_dir=""):
    """Drop-in replacement for QtWidgets.QFileDialog.getExistingDirectory's
    static convenience method, for the same reason _message_box replaces
    QMessageBox's (confirmed directly in data_integrity's dm_integrity_gui.py -
    "Browse..." reproduced the identical no-error-nothing-visible symptom).
    DontUseNativeDialog matters here specifically: getExistingDirectory
    defaults to the platform's own native picker when available, which is
    a separate windowing stack outside Qt's show()/raise_()/
    activateWindow() control - _center_on_parent can't do anything for a
    window it was never involved in creating."""
    dialog = QtWidgets.QFileDialog(parent, title, start_dir)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    _center_on_parent(dialog, parent)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        selected = dialog.selectedFiles()
        return selected[0] if selected else ""
    return ""


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


class _TopFoldersWorker(QtCore.QObject):
    """Runs `du` over the target's entire tree off the GUI thread, via
    dm.spawn_du()/_parse_du_output() rather than the CLI's blocking
    dm.top_level_breakdown() - this needs to hold onto the live Popen so
    cancel() (see TopFoldersDialog._cancel_and_wait) can kill it early. On
    a multi-TB beamline mount this can run for many minutes; running it
    inline would freeze the whole GUI for that whole time, and letting Qt
    tear down a QThread while du is still running underneath it prints
    "QThread: Destroyed while thread is still running" and can hang/crash
    - confirmed directly by closing this dialog mid-scan on s20a before
    cancel() existed.
    """

    finished = QtCore.pyqtSignal(list)
    error = QtCore.pyqtSignal(str)

    def __init__(self, path, top_n):
        super().__init__()
        self.path = path
        self.top_n = top_n
        self._proc = None
        self._cancelled = False

    def run(self):
        if self._cancelled:
            return
        try:
            proc = dm.spawn_du(self.path)
        except RuntimeError as e:
            self.error.emit(str(e))
            return
        self._proc = proc
        stdout, stderr = proc.communicate()

        if self._cancelled:
            # cancel() already killed the process and this dialog is on
            # its way out - nothing left to report to, and touching UI
            # signals here would race with the dialog tearing itself down.
            return

        if proc.returncode != 0 and not stdout.strip():
            self.error.emit(f"du failed for {self.path}: {stderr.strip()}")
            return

        entries = dm._parse_du_output(stdout, self.path)[: self.top_n]
        self.finished.emit(entries)

    def cancel(self):
        """Called from the GUI thread (see _cancel_and_wait) when the
        dialog is closing before the scan finished - kill the still-running
        du subprocess so run()'s communicate() call returns immediately
        instead of leaving du (and this worker's thread) running for
        however much longer the target's full tree walk would otherwise
        take. Safe to call whether or not du has started yet: the
        _cancelled flag makes run() a no-op if it hasn't spawned du yet."""
        self._cancelled = True
        if self._proc is not None and self._proc.poll() is None:
            self._proc.kill()


class TopFoldersDialog(QtWidgets.QDialog):
    """Shows the largest top-level subdirectories of one monitored target,
    each with its size and most recent modification time (recursively) -
    a starting point for deciding what's safe to clean up. Scans in the
    background (see _TopFoldersWorker); closing this dialog (Close button,
    Escape, or window close) before the scan finishes cancels it and waits
    for the worker thread to actually stop first, rather than letting Qt
    destroy a QThread that's still running underneath it.
    """

    def __init__(self, parent, name, path, top_n=5):
        super().__init__(parent)
        self.setWindowTitle(f"Top folders in '{name}'")
        self.resize(600, 300)

        layout = QtWidgets.QVBoxLayout(self)
        self.status_label = QtWidgets.QLabel(f"Scanning {path} ...")
        layout.addWidget(self.status_label)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Folder", "Size (GB)", "Last updated"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._thread = QtCore.QThread(self)
        self._worker = _TopFoldersWorker(path, top_n)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _cancel_and_wait(self):
        """Stop a still-running scan cooperatively before this dialog is
        actually allowed to close: kill the du subprocess (see
        _TopFoldersWorker.cancel), then block briefly for the worker
        thread to notice and exit. A bounded wait, not an unconditional
        one - if du is wedged on a hung NFS mount (uninterruptible I/O
        wait, where even SIGKILL can't land until the syscall returns),
        this gives up after 5s and lets the dialog close anyway rather
        than freezing the GUI indefinitely; the thread will still finish
        and clean itself up whenever du actually exits, just later.
        """
        if self._thread.isRunning():
            self._worker.cancel()
            self._thread.quit()
            self._thread.wait(5000)

    def reject(self):
        self._cancel_and_wait()
        super().reject()

    def closeEvent(self, event):
        self._cancel_and_wait()
        super().closeEvent(event)

    def _on_finished(self, entries):
        if not entries:
            self.status_label.setText("No subdirectories found (or none were readable).")
            return

        self.status_label.setText(f"{len(entries)} largest subdirectories, by size:")
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            size_gb = entry["size_bytes"] / dm.GB
            mtime = entry["mtime"]
            mtime_str = (
                QtCore.QDateTime.fromSecsSinceEpoch(int(mtime)).toString(QtCore.Qt.TextDate)
                if mtime is not None else "unknown"
            )
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(entry["name"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem("{:.2f}".format(size_gb)))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(mtime_str))
        self.table.resizeColumnsToContents()

    def _on_error(self, message):
        self.status_label.setText(f"Scan failed: {message}")


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
        path = _choose_directory(self, "Select directory")
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
        toolbar.addAction("Top folders...", self.show_top_folders)

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
        _center_on_parent(dialog, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        target = dialog.target()
        if not target["name"] or not target["path"]:
            _message_box(QtWidgets.QMessageBox.Warning, self, "Missing fields", "Name and path are required.")
            return

        self.cfg["targets"].append(target)
        dm.save_config(self.cfg, self.config_path)
        self.refresh()

    def edit_recipients(self):
        # A real QDialog we build and pre-fill ourselves, not QInputDialog.
        # getText's static convenience method - confirmed directly that
        # the static call's own pre-fill text argument silently failed to
        # show (an empty field even with real, non-empty recipients
        # already configured), the same class of black-box-static-dialog
        # trouble every other one of these has caused this session. One
        # address per line (not comma-separated) is also just easier to
        # read/edit for more than a couple of recipients.
        current = "\n".join(self.cfg["settings"].get("recipients", []))

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Alert recipients")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel("One email address per line:"))
        text_edit = QtWidgets.QPlainTextEdit()
        text_edit.setPlainText(current)
        layout.addWidget(text_edit)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(400, 300)
        _center_on_parent(dialog, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        # Still tolerates commas within a line, not just newlines - a
        # pasted old-style "a@x.com, b@x.com" line keeps working rather
        # than silently becoming one malformed address.
        addrs = [addr.strip() for line in text_edit.toPlainText().splitlines()
                 for addr in line.split(",") if addr.strip()]
        self.cfg["settings"]["recipients"] = addrs
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
            _message_box(QtWidgets.QMessageBox.Warning, self, "No targets", "No valid targets to test.")
            return

        status = dict(valid[rows[0]] if rows else valid[0])
        status["level"] = "alert"
        ok = dm.send_alert_email(self.cfg, status, all_statuses=valid)
        if ok:
            _message_box(QtWidgets.QMessageBox.Information, self, "Test email", "Test alert sent (or printed to console).")
        else:
            _message_box(QtWidgets.QMessageBox.Critical, self, "Test email failed", "Failed to send test email; see console.")

    def show_top_folders(self):
        """Manual, on-demand deep dive for one target - the full recursive
        breakdown of every top-level subfolder's size, not just the whole-
        target total shown in the table. Only enabled per-row (needs a
        selection) since running it for every target at once would be a
        multi-target concurrent `du` storm; also relies on the single-
        selection-row assumption refresh() relies on."""
        targets = self.cfg.get("targets", [])
        if not targets:
            _message_box(QtWidgets.QMessageBox.Warning, self, "No targets", "No monitored paths configured.")
            return

        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        row = rows[0] if rows else 0
        target = targets[row]

        dialog = TopFoldersDialog(self, target["name"], target["path"])
        _center_on_parent(dialog, self)
        dialog.exec_()


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
