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

COLUMNS = ["Name", "Path", "Used %", "Free (GB)", "Rate (GB/hr)", "ETA (days)", "Threshold %", "Status", "Recent activity"]

DEFAULT_FONT_SIZE = 10

LEVEL_COLORS = {
    "ok": QtGui.QColor("#c8f7c5"),
    "warn": QtGui.QColor("#fff3b0"),
    "alert": QtGui.QColor("#f7c5c5"),
    "error": QtGui.QColor("#e0e0e0"),
    "unknown": QtGui.QColor("#e0e0e0"),
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

    Returns (text, level), where level is one of "ok"/"alert"/"unknown" -
    used to color the toolbar badge the same way the main table's Status
    column is colored (see LEVEL_COLORS), so a dead/unscheduled cron job
    (which means disk checks and alert emails stop happening the moment
    nobody has this GUI open) is as visually obvious as a red table row.
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
        return "Disk monitor: SERVICE DOWN", "alert"
    if job_scheduled is False:
        return "Disk monitor: not scheduled", "alert"
    if service_active and job_scheduled:
        return "Disk monitor: OK", "ok"
    return "Disk monitor: unknown", "unknown"


def _format_age(mtime):
    """epoch seconds -> compact relative string ('2h ago', '3d ago') for
    the 'Recent activity' column/tooltip - the raw epoch or a full
    timestamp is too dense to scan across a whole table at a glance."""
    if mtime is None:
        return "unknown"
    delta = max(0, time.time() - mtime)
    if delta < 3600:
        return "{:.0f}m ago".format(delta / 60)
    if delta < 86400:
        return "{:.0f}h ago".format(delta / 3600)
    return "{:.0f}d ago".format(delta / 86400)


def _top_folder_summary(entries):
    """(cell_text, tooltip_text) for the 'Recent activity' column from a
    full (uncapped) top-level du entries list. Size and recency are two
    independent, often unrelated signals - a folder can be huge but
    untouched for months, or tiny but being written to right now - so
    this ranks by each separately rather than picking one list and
    re-sorting it by the other criterion (which would silently hide a
    small-but-active folder that never makes a size-based top N). Cell
    text stays a single compact "most recently touched" line for an
    at-a-glance signal; the tooltip breaks out both top-3 rankings in
    full."""
    if not entries:
        return "(empty)", "No subdirectories found (or none were readable)."

    by_size = sorted(entries, key=lambda e: e["size_bytes"], reverse=True)[:3]
    by_recency = sorted(entries, key=lambda e: e["mtime"] or 0, reverse=True)[:3]

    top_recent = by_recency[0]
    cell_text = "{} ({})".format(top_recent["name"], _format_age(top_recent["mtime"]))

    def _line(e):
        size_gb = e["size_bytes"] / dm.GB
        return "{}  -  {:.1f} GB  -  {}".format(e["name"], size_gb, _format_age(e["mtime"]))

    tooltip_lines = ["Top 3 largest:"]
    tooltip_lines += [_line(e) for e in by_size]
    tooltip_lines.append("")
    tooltip_lines.append("Top 3 most recently edited:")
    tooltip_lines += [_line(e) for e in by_recency]
    return cell_text, "\n".join(tooltip_lines)


class _TopFoldersBackgroundScanner(QtCore.QObject):
    """Scans every monitored target's top-level folders sequentially (one
    `du` at a time, not all targets in parallel - several concurrent full
    recursive walks of multi-TB NFS mounts would just contend with each
    other and the beamline's own I/O for no real speed gain), off the GUI
    thread, so the 'Recent activity' column can populate itself once at
    startup without freezing the table. Emits target_done(name, entries)
    incrementally so each row updates as soon as its own scan finishes,
    rather than waiting for every target to complete first.
    """

    target_done = QtCore.pyqtSignal(str, object)  # name, entries (or None on failure)
    all_done = QtCore.pyqtSignal()

    def __init__(self, targets):
        super().__init__()
        self._targets = targets  # [(name, path), ...]
        self._proc = None
        self._cancelled = False

    def run(self):
        for name, path in self._targets:
            if self._cancelled:
                return
            try:
                proc = dm.spawn_du(path)
            except RuntimeError:
                self.target_done.emit(name, None)
                continue
            self._proc = proc
            stdout, stderr = proc.communicate()
            self._proc = None
            if self._cancelled:
                return
            if proc.returncode != 0 and not stdout.strip():
                self.target_done.emit(name, None)
                continue
            # Uncapped: _top_folder_summary needs every entry to rank by
            # size and by recency independently, not just whichever subset
            # a single size-based top N would have kept.
            entries = dm._parse_du_output(stdout, path)
            self.target_done.emit(name, entries)
        self.all_done.emit()

    def cancel(self):
        """Same idea as _TopFoldersWorker.cancel() - kill whichever du is
        currently running so this thread winds down promptly instead of
        working through the rest of the target list first."""
        self._cancelled = True
        if self._proc is not None and self._proc.poll() is None:
            self._proc.kill()


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

    def __init__(self, path):
        super().__init__()
        self.path = path
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

        # Uncapped - the dialog itself slices to top_n for its own "N
        # largest, by size" table, but DiskMonitorPanel.show_top_folders
        # reuses the full list (via result_entries) to refresh the
        # "Recent activity" column's independent size/recency rankings.
        entries = dm._parse_du_output(stdout, self.path)
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
        self.top_n = top_n  # caps only this dialog's own table, not result_entries
        self.result_entries = None  # full list, set on completion; read by DiskMonitorPanel.show_top_folders

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
        self._worker = _TopFoldersWorker(path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

        # Tracks whether the worker has wound down, via the same
        # finished/error signals that already drive UI updates - NOT by
        # querying self._thread's own isRunning()/etc. at close time.
        # Confirmed directly this distinction matters: if the scan
        # finishes naturally while the dialog is still open (the common
        # case for anything but a huge mount), self._thread.finished's
        # deleteLater() destroys the underlying C++ QThread well before
        # the dialog is ever closed - so closeEvent()/reject() touching
        # self._thread at all (even just .isRunning()) raises "wrapped
        # C/C++ object of type QThread has been deleted", on the very
        # first close attempt, regardless of how many times cleanup runs.
        self._scan_done = False
        self._cleanup_done = False

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

        Idempotent (both reject() and closeEvent() call this, and in
        practice one action can trigger both), and safe to call after the
        scan has already finished on its own - see the note in __init__
        for why that case must never touch self._thread at all.
        """
        if self._cleanup_done:
            return
        self._cleanup_done = True
        if self._scan_done:
            return
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
        self._scan_done = True
        self.result_entries = entries  # full list; read by DiskMonitorPanel.show_top_folders to refresh its cached summary column
        if not entries:
            self.status_label.setText("No subdirectories found (or none were readable).")
            return

        display_entries = entries[: self.top_n]
        self.status_label.setText(f"{len(display_entries)} largest subdirectories, by size:")
        self.table.setRowCount(len(display_entries))
        for row, entry in enumerate(display_entries):
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
        self._scan_done = True
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

        # name -> (cell_text, tooltip_text) from the last completed top-
        # folders scan for that target, populated once in the background
        # at startup (see _start_activity_scan) and refreshed whenever the
        # "Top folders..." dialog is used manually - never recomputed on
        # the fast refresh()/timer cadence, since it's a full recursive du
        # walk, not a cheap statvfs call.
        self._activity_cache = {}
        self._activity_thread = None
        self._activity_scanner = None
        # True whenever there's no scan in flight (including "never
        # started one yet") - checked instead of self._activity_thread.
        # isRunning() in shutdown(), for the exact same reason
        # TopFoldersDialog tracks _scan_done rather than querying the
        # QThread directly: if a scan already finished naturally before
        # shutdown() is called, the thread's own finished-signal-driven
        # deleteLater() has already destroyed the underlying C++ object,
        # and querying it at all (even just .isRunning()) raises "wrapped
        # C/C++ object of type QThread has been deleted."
        self._activity_scan_done = True

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

        # Real QPushButtons, not toolbar.addAction() - a QAction shown in a
        # QToolBar renders as flat, borderless text on this Qt style/
        # platform, visually indistinguishable from a plain label. A
        # QPushButton always renders with a visible raised/bordered look
        # regardless of style, matching how dm_integrity_gui.py's own
        # "Add EXPID..." button already does it.
        for label, handler in [
            ("Refresh now", self.refresh),
            ("Add path...", self.add_path),
            ("Remove selected", self.remove_selected),
            ("Edit recipients...", self.edit_recipients),
            ("Send test email", self.send_test_email),
            ("Top folders...", self.show_top_folders),
        ]:
            btn = QtWidgets.QPushButton(label)
            btn.clicked.connect(handler)
            toolbar.addWidget(btn)

        toolbar.addSeparator()
        self.cron_label = QtWidgets.QLabel(" Disk monitor: checking... ")
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
        self._start_activity_scan()

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

        cron_text, cron_level = _cron_status(os.path.join(dm.SCRIPT_DIR, "disk_monitor.py"))
        self.cron_label.setText(" {} ".format(cron_text))
        self.cron_label.setStyleSheet(
            "background-color: {};".format(LEVEL_COLORS[cron_level].name()))

        self.table.setRowCount(len(statuses))
        for row, s in enumerate(statuses):
            activity_text, activity_tooltip = self._activity_cache.get(
                s["name"], ("Scanning...", "Top-folders scan in progress or not yet started."))

            if s.get("level") == "error":
                values = [s["name"], s["path"], "-", "-", "-", "-", "-", "ERROR: " + s["error"], activity_text]
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
                    activity_text,
                ]

            color = LEVEL_COLORS.get(s.get("level"), LEVEL_COLORS["error"])
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setBackground(color)
                if col == len(values) - 1:
                    item.setToolTip(activity_tooltip)
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
        self._start_activity_scan()  # new target has no cached summary yet

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
        self._start_activity_scan()  # don't keep scanning a target that's no longer monitored

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
        """Open TopFoldersDialog for the selected row's target (or the
        first target if none selected) - same row-selection convention as
        send_test_email above, and the same row-index-matches-cfg[targets]-
        order assumption refresh() relies on."""
        targets = self.cfg.get("targets", [])
        if not targets:
            _message_box(QtWidgets.QMessageBox.Warning, self, "No targets", "No monitored paths configured.")
            return

        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        row = rows[0] if rows else 0
        if row >= len(targets):
            row = 0
        target = targets[row]

        dialog = TopFoldersDialog(self, target["name"], target["path"])
        _center_on_parent(dialog, self)
        dialog.exec_()

        # A manual scan is strictly more current than whatever the
        # background startup scan cached (or hasn't gotten to yet) - feed
        # it back into the same cache the "Recent activity" column reads,
        # rather than leaving that column stuck showing older/placeholder
        # text until the next full GUI restart.
        if dialog.result_entries is not None:
            self._update_activity_cache(target["name"], dialog.result_entries)

    def _update_activity_cache(self, name, entries):
        self._activity_cache[name] = _top_folder_summary(entries)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == name:
                text, tooltip = self._activity_cache[name]
                cell = QtWidgets.QTableWidgetItem(text)
                cell.setBackground(self.table.item(row, len(COLUMNS) - 1).background())
                cell.setToolTip(tooltip)
                self.table.setItem(row, len(COLUMNS) - 1, cell)
                break

    def _start_activity_scan(self):
        """Kick off the one-time (per GUI launch) background scan that
        populates the 'Recent activity' column for every configured
        target - see _TopFoldersBackgroundScanner. Safe to call again
        later (e.g. after Add path/Remove selected change the target
        list) since it always starts a fresh scanner over the current
        target list; callers don't need to cancel an old one first, that
        happens automatically in shutdown()/before a fresh scan replaces
        self._activity_scanner.
        """
        self.shutdown()  # cancel any still-running scan over a now-stale target list first

        targets = [(t["name"], t["path"]) for t in self.cfg.get("targets", [])]
        if not targets:
            return

        self._activity_scan_done = False
        self._activity_thread = QtCore.QThread(self)
        self._activity_scanner = _TopFoldersBackgroundScanner(targets)
        self._activity_scanner.moveToThread(self._activity_thread)
        self._activity_thread.started.connect(self._activity_scanner.run)
        self._activity_scanner.target_done.connect(self._on_activity_target_done)
        self._activity_scanner.all_done.connect(self._on_activity_all_done)
        self._activity_scanner.all_done.connect(self._activity_thread.quit)
        self._activity_thread.finished.connect(self._activity_thread.deleteLater)
        self._activity_thread.start()

    def _on_activity_target_done(self, name, entries):
        self._update_activity_cache(name, entries)

    def _on_activity_all_done(self):
        self._activity_scan_done = True

    def shutdown(self):
        """Cancel the background activity scanner if it's still running -
        called before starting a fresh one, and should also be called from
        whatever top-level window hosts this panel on its own closeEvent
        (see ops_gui.py/DiskMonitorWindow), for the same reason
        TopFoldersDialog needs its own cancel-and-wait: letting Qt tear
        down a QThread that's still running underneath it is unsafe.

        Deliberately checks self._activity_scan_done rather than
        self._activity_thread.isRunning() - see the note on that flag in
        __init__ for why touching the QThread object at all isn't safe
        once a scan may have already finished on its own.
        """
        if self._activity_scan_done:
            return
        if self._activity_scanner is not None:
            self._activity_scanner.cancel()
        if self._activity_thread is not None:
            self._activity_thread.quit()
            self._activity_thread.wait(5000)
        self._activity_scan_done = True


class DiskMonitorWindow(QtWidgets.QMainWindow):
    """Standalone window hosting DiskMonitorPanel - used when this file is
    run directly rather than embedded as a tab in ops_gui.py."""

    def __init__(self, config_path):
        super().__init__()
        self.setWindowTitle("Disk Space Monitor")
        self.resize(900, 400)
        self.panel = DiskMonitorPanel(config_path)
        self.setCentralWidget(self.panel)

    def closeEvent(self, event):
        self.panel.shutdown()
        super().closeEvent(event)


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
