#!/usr/bin/env python3
"""
Data integrity GUI: PyQt5 panel for monitoring experiment upload integrity.
Dashboard view shows recent 10 experiments with file statistics and status.
"""

import json
import os
import shlex
import sys
import time
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    import dm_integrity as di
except ImportError:
    di = None


LEVEL_COLORS = {
    "OK": QtGui.QColor(0, 128, 0),
    "WARNING": QtGui.QColor(255, 165, 0),
    "ERROR": QtGui.QColor(255, 0, 0),
    "INFO": QtGui.QColor(0, 0, 255),
}

STATUS_COLORS = {
    "good": QtGui.QColor(144, 238, 144),
    "attention": QtGui.QColor(255, 255, 200),
    "problem": QtGui.QColor(255, 200, 200),
    "noncritical": QtGui.QColor(255, 220, 150),
    "in_progress": QtGui.QColor(200, 220, 255),
    "stale": QtGui.QColor(255, 200, 200),
}

# Terminal checksum-job states - once a tracked job reaches one of these,
# polling stops treating it as active.
_CHECKSUM_TERMINAL_STATES = ("DONE", "FAILED", "CANCELLED")

# checksum_worker.py only calls progress_cb (which writes status - see
# STATUS_WRITE_INTERVAL_SEC in checksum_worker.py) once per whole file
# hashed, not per chunk within one - so the real gap between writes scales
# with this beamline's actual file sizes, not a fixed small interval.
# Confirmed directly against real data: pokharel_jul26's ge5/*.h5 detector
# files are ~30GB EACH, and a single one can legitimately take several
# minutes to read+hash over NFS with zero progress_cb calls in between -
# initially set to 120s on the (wrong) assumption that per-file gaps would
# stay in the tens-of-seconds range, which produced a false "Stalled?" on
# a job that was actually alive and correctly working through a huge file
# (confirmed via `ps`: real, ongoing CPU consumption on the remote host).
# 900s (15min) still comfortably catches the two real cases that motivated
# this feature at all - jobs that sat at RUNNING for 78 hours and 20 hours
# after their process actually died (see checksum_worker.py's ENOSPC
# traceback in that incident) - while giving real multi-GB files enough
# room not to trip a false alarm.
_CHECKSUM_STALE_SEC = 900


def _format_age(seconds):
    """Human-friendly elapsed time for a staleness indicator - "3h", "45m",
    "20d" - coarse on purpose, this is only ever used to say "a while", not
    to give a precise duration."""
    seconds = max(0, seconds)
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // 86400)}d"


def _center_on_parent(dialog, parent):
    """Explicitly position dialog over parent's current on-screen geometry
    before it's shown, rather than trusting the window manager/compositor's
    default placement for a new top-level window - confirmed necessary on
    at least one real deployment: a Wayland/Mutter compositor with an
    unusual multi-monitor layout placed brand-new, position-less windows
    entirely off every monitor. An explicit move() issued after a window
    is already mapped gets silently overridden by that same compositor,
    but a position requested before the window is first shown is honored.
    No-op if parent isn't currently visible (e.g. a dialog opened before
    the main window is shown) - nothing sensible to center on yet."""
    if parent is None or not parent.isVisible():
        return
    # adjustSize() first, but ONLY for a dialog that never explicitly
    # resize()d itself (e.g. AddExperimentDialog, sized purely by its
    # layout) - it otherwise still reports a placeholder width/height at
    # this point, which would center it wrong once it snaps to its real
    # size. WA_Resized is set automatically by resize() (Qt's own way of
    # tracking "has this widget been given an explicit size"), so this
    # skips adjustSize() for a dialog like HistoryDetailDialog that
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
    # entirely on/past a neighboring monitor with a different origin - a
    # modal HistoryDetailDialog reproduced exactly this (main window
    # provably blocked by the modal dialog, nothing visible anywhere).
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
    # sufficient on their own (confirmed directly - History/Add EXPID
    # produced no window, no taskbar entry, and no error either).
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
    explicit-positioning fix _center_on_parent already applies to every
    custom QDialog here. Those static methods constructed and exec_'d their
    own QMessageBox internally with no hook to position it first - on the
    same Wayland/Mutter setup that placed brand-new top-level windows
    off-screen by default (see _center_on_parent's docstring), a plain
    QMessageBox.information() call is just as invisible as an unpositioned
    QDialog would have been. Confirmed directly: History's own "No records
    found" QMessageBox.information call (the one plain call site nothing
    else in this file routed through _center_on_parent) reproduced exactly
    that symptom - clicking History for an experiment with zero saved
    records appeared to do nothing at all.
    """
    box = QtWidgets.QMessageBox(icon, title, text, buttons, parent)
    if default_button is not None:
        box.setDefaultButton(default_button)
    _center_on_parent(box, parent)
    return box.exec_()


def _choose_directory(parent, title, start_dir=""):
    """Drop-in replacement for QtWidgets.QFileDialog.getExistingDirectory's
    static convenience method, for the same reason _message_box replaces
    QMessageBox's - confirmed directly, "Browse..." in AddExperimentDialog
    reproduced the identical symptom (no error, nothing visible) every
    other unpositioned dialog in this file already had.

    DontUseNativeDialog is the key difference from _message_box, not just
    the positioning: getExistingDirectory defaults to the platform's own
    native picker (GTK's, here) when available, which is a completely
    separate windowing stack outside Qt's show()/raise_()/activateWindow()
    control - _center_on_parent can't do anything for a window it was
    never involved in creating. Forcing Qt's own implementation keeps this
    dialog on the same footing (and the same fix) as every other one here.
    """
    dialog = QtWidgets.QFileDialog(parent, title, start_dir)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    _center_on_parent(dialog, parent)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        selected = dialog.selectedFiles()
        return selected[0] if selected else ""
    return ""


class _ScanWorker(QtCore.QObject):
    """Runs a Scan pass off the GUI thread - get_upload_status/
    get_catalog_files are SSH round-trips (seconds each), which would
    otherwise freeze the whole window (Qt's event loop is single-threaded).

    Scan-only: Verify MD5's hashing loop is far too slow to run this way
    (many minutes for a large experiment) and instead runs as a detached
    systemd --user job on zion - see _ChecksumLaunchWorker and
    checksum_worker.py. Scan's own computation is unchanged from before
    that split; only its final save is different (save_record_remote, so
    Scan's results land in the beamline's shared dm_record/ regardless of
    which account launched the GUI, not wherever Scan happened to run).
    """

    finished = QtCore.pyqtSignal(dict)
    error = QtCore.pyqtSignal(str)

    def __init__(self, exp_name, station_name, remote_host, remote_user, setup_script,
                 local_root, dataset, save_host, save_user, remote_base, legacy_records_dir):
        super().__init__()
        self.exp_name = exp_name
        self.station_name = station_name
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.setup_script = setup_script
        self.local_root = local_root
        self.dataset = dataset
        self.save_host = save_host
        self.save_user = save_user
        # remote_base is None only if this beamline has no checksum_hosts
        # entry configured - falls back to the old purely-local save/no
        # locking behavior rather than crashing, though the shipped config
        # always has both s1/s20 entries.
        self.remote_base = remote_base
        self.legacy_records_dir = legacy_records_dir

    def run(self):
        # Guard rail: two Scans for the same experiment, launched from
        # different users'/sessions' own GUI instances, would otherwise
        # race harmlessly-but-wastefully (duplicate DM queries) with no
        # visibility into each other (unlike Verify MD5, Scan has no
        # shared status file - a systemd unit's own uniqueness doesn't
        # apply here either, since Scan runs in-process, not as a
        # detached job). mkdir-based lock, atomic, shared across every
        # launcher via the beamline's own dm_record/locks/.
        lock_path = di.lock_dir(self.remote_base, "scan", self.exp_name) if self.remote_base else None
        if lock_path and not di.acquire_remote_lock(self.save_host, self.save_user, lock_path):
            self.error.emit(f"Scan already running for '{self.exp_name}' (started by another user or session)")
            return

        try:
            upload_status = di.get_upload_status(
                self.exp_name, self.station_name, self.remote_host, self.remote_user, self.setup_script)
            catalog_files = di.get_catalog_files(
                self.exp_name, self.dataset, self.station_name, self.remote_host, self.remote_user, self.setup_script)
            local_files = di.scan_local_files(self.local_root)
            comparison = di.compare(local_files, catalog_files)

            report = di.build_report(self.exp_name, upload_status, comparison)
            if self.remote_base:
                di.save_record_remote(self.save_host, self.save_user, di.checksum_records_dir(self.remote_base), self.exp_name, report)
            else:
                di.save_record(self.legacy_records_dir, self.exp_name, report)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if lock_path:
                di.release_remote_lock(self.save_host, self.save_user, lock_path)


class _ChecksumLaunchWorker(QtCore.QObject):
    """Prepares and launches a detached Verify MD5 job on zion, off the GUI
    thread. Does the same fast DM-catalog SSH queries Scan does (unchanged
    routing - settings.remote_hosts/setup_scripts), then writes the job
    spec + initial QUEUED status into the beamline's shared dm_record/ and
    launches checksum_worker.py there via systemd-run --user. This worker's
    own job ends the moment the launch succeeds - the actual hashing is
    checksum_worker.py's problem from then on, detached and independent of
    this GUI process."""

    launched = QtCore.pyqtSignal(dict)   # the initial QUEUED status dict, for tracking
    error = QtCore.pyqtSignal(str)

    def __init__(self, exp_name, beamline, station_name, dm_remote_host, dm_remote_user, dm_setup_script,
                 local_root, dataset, checksum_host, checksum_user, remote_base, cpu_budget, all_status_dirs):
        super().__init__()
        self.exp_name = exp_name
        self.beamline = beamline
        self.station_name = station_name
        self.dm_remote_host = dm_remote_host
        self.dm_remote_user = dm_remote_user
        self.dm_setup_script = dm_setup_script
        self.local_root = local_root
        self.dataset = dataset
        self.checksum_host = checksum_host
        self.checksum_user = checksum_user
        self.remote_base = remote_base
        self.cpu_budget = cpu_budget
        self.all_status_dirs = all_status_dirs

    def run(self):
        # Guard rail: the status-file pre-check in _launch_checksum_job
        # (GUI thread) is a fast common-case filter, but it's a
        # check-then-act race across different users'/sessions' own GUI
        # instances - two launches close together could both pass that
        # check before either has written QUEUED. This mkdir-based lock
        # closes that race properly (atomic, shared across every launcher
        # via the beamline's own dm_record/locks/); it only needs to cover
        # the launch sequence itself, not the job's whole runtime - once
        # started, the systemd unit's own uniqueness plus the RUNNING
        # status file are what "already running" means for the rest of
        # the job's life.
        lock_path = di.lock_dir(self.remote_base, "checksum", self.exp_name)
        if not di.acquire_remote_lock(self.checksum_host, self.checksum_user, lock_path):
            self.error.emit(f"Verification already running for '{self.exp_name}' (started by another user or session)")
            return

        try:
            # Re-check now that we hold the lock: someone else's launch may
            # have completed between the GUI thread's pre-check and here.
            status_path = di.checksum_status_path(self.remote_base, self.exp_name)
            try:
                with open(status_path) as f:
                    existing = json.load(f)
                if existing.get("state") in ("QUEUED", "RUNNING"):
                    self.error.emit(f"Verification already running for '{self.exp_name}' (started by another user or session)")
                    return
            except (OSError, json.JSONDecodeError):
                pass

            upload_status = di.get_upload_status(
                self.exp_name, self.station_name, self.dm_remote_host, self.dm_remote_user, self.dm_setup_script)
            catalog_files = di.get_catalog_files(
                self.exp_name, self.dataset, self.station_name, self.dm_remote_host, self.dm_remote_user, self.dm_setup_script)
            local_files = di.scan_local_files(self.local_root)
            comparison = di.compare(local_files, catalog_files)
            paths_to_verify = [p for p, s in comparison.items() if s == "MATCH"]

            unit_name = di.checksum_unit_name(self.exp_name)
            # Deliberately NOT ".job.json" - _count_active_peers globs
            # STATUS_SUFFIX (".json") across both beamlines' status dirs to
            # find active peers, and a job spec can be many MB for a large
            # experiment's full catalog (confirmed: 17MB for one real
            # experiment). An extension that doesn't end in ".json" at all
            # means that glob structurally can't match it, rather than
            # relying on an exclusion check to get it right every time.
            job_spec_path = os.path.join(di.checksum_status_dir(self.remote_base), f"{self.exp_name}.jobspec")
            records_dir = di.checksum_records_dir(self.remote_base)

            job_spec = {
                "experiment_name": self.exp_name,
                "beamline": self.beamline,
                "local_root": self.local_root,
                "upload_status": upload_status,
                "catalog_files": catalog_files,
                "comparison": comparison,
                "paths_to_verify": paths_to_verify,
                "records_dir": records_dir,
                "status_dirs": self.all_status_dirs,
                "cpu_budget": self.cpu_budget,
            }

            now = time.time()
            queued_status = {
                "schema_version": 1,
                "experiment_name": self.exp_name,
                "beamline": self.beamline,
                "state": "QUEUED",
                "unit_name": unit_name,
                "queued_at": now,
                "updated_at": now,
                "total_files": len(paths_to_verify),
                "checked_files": 0,
            }

            di.write_remote_file(self.checksum_host, self.checksum_user, job_spec_path, json.dumps(job_spec, indent=2))
            di.write_remote_file(self.checksum_host, self.checksum_user, status_path, json.dumps(queued_status, indent=2))
            di.launch_checksum_job(
                self.checksum_host, self.checksum_user, unit_name, job_spec_path, status_path,
                os.path.join(SCRIPT_DIR, "checksum_worker.py"))

            self.launched.emit(queued_status)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            di.release_remote_lock(self.checksum_host, self.checksum_user, lock_path)


class HistoryDetailDialog(QtWidgets.QDialog):
    """Drill-down for one experiment's saved Scan/Verify MD5 records - which
    specific files are missing from Sojourner, which are size- or
    checksum-mismatched, and which whole subdirectories never landed at
    all. The prior "History" view (a plain QMessageBox of good/bad counts
    per past run) could say *that* something was wrong but never *what* -
    this reads the same report already saved to disk (report["comparison"],
    ["checksum_results"], ["directory_stats"]) and just surfaces the detail
    that was always computed but never shown.
    """

    # Built per-instance (see __init__) rather than as this class-level
    # default, since LOCAL_ONLY/REMOTE_ONLY read more clearly naming the
    # actual side ("s1c"/"s20a") than the generic "locally" they'd
    # otherwise say regardless of which beamline's experiment this is.
    _CATEGORY_LABELS_DEFAULT = {
        "LOCAL_ONLY": "Missing from Sojourner",
        "REMOTE_ONLY": "On Sojourner, not found locally",
        "SIZE_MISMATCH": "Size mismatch",
        "CHECKSUM_MISMATCH": "Checksum mismatch",
        "CHECKSUM_ERROR": "Checksum error (couldn't verify)",
    }

    def __init__(self, parent, exp_name, records, local_label="local"):
        """records: [(timestamp, filepath), ...] oldest-first (list_records'
        own return shape) - shown most-recent-first in the picker.
        local_label: basename of this experiment's local_bases entry (e.g.
        "s1c"/"s20a") - used only to name the LOCAL_ONLY/REMOTE_ONLY
        categories below, never for path computation."""
        super().__init__(parent)
        self.setWindowTitle(f"History for '{exp_name}'")
        self.resize(900, 550)
        self._records = list(reversed(records))
        self._category_labels = dict(self._CATEGORY_LABELS_DEFAULT)
        self._category_labels["LOCAL_ONLY"] = f"On {local_label}, not on Sojourner"
        self._category_labels["REMOTE_ONLY"] = f"On Sojourner, not on {local_label}"
        self._relocated_label = f"Relocated (same file, different path under {local_label})"
        self._all_rows = []  # (path, category_key, issue_label) for the currently loaded snapshot - filtered into self.table by _apply_filter

        layout = QtWidgets.QVBoxLayout(self)

        picker_row = QtWidgets.QHBoxLayout()
        picker_row.addWidget(QtWidgets.QLabel("Snapshot:"))
        self.snapshot_combo = QtWidgets.QComboBox()
        for timestamp, _ in self._records:
            self.snapshot_combo.addItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)))
        picker_row.addWidget(self.snapshot_combo)
        picker_row.addStretch()
        layout.addLayout(picker_row)

        self.summary_label = QtWidgets.QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # Category -> count tabulation (good/bad broken down, plus
        # relocated) - the free-text summary_label above only ever gave
        # aggregate good/bad/relocated totals, never which categories of
        # "bad" (missing vs mismatched vs error) made up that count or how
        # many. One row per category actually present in this snapshot, so
        # an all-good snapshot shows just a single "Good" row rather than
        # five zero rows.
        self.stats_table = QtWidgets.QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["Category", "Count"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setMaximumHeight(160)
        self.stats_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        layout.addWidget(self.stats_table)

        # Bounded, scrollable box, not a plain word-wrapped QLabel: an
        # experiment with dozens of whole missing subdirectories (a real
        # case, not hypothetical) wrapped into enough lines to push the
        # actual per-file table down to a sliver at the bottom of the
        # dialog - the more useful, actionable content squeezed out by the
        # less useful summary text above it. Same fixed-height-QPlainTextEdit
        # pattern already used for the console (see DataIntegrityPanel._init_ui).
        self.dirs_label = QtWidgets.QPlainTextEdit()
        self.dirs_label.setReadOnly(True)
        self.dirs_label.setMaximumHeight(100)
        layout.addWidget(self.dirs_label)

        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel("Show:"))
        self.filter_combo = QtWidgets.QComboBox()
        filter_row.addWidget(self.filter_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["File", "Issue"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table, 1)  # stretch factor: the table gets any extra space, not the fixed-height widgets around it

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.snapshot_combo.currentIndexChanged.connect(self._load_snapshot)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        self._load_snapshot(0)

    def _load_snapshot(self, index):
        if index < 0 or index >= len(self._records):
            return
        _, filepath = self._records[index]
        try:
            with open(filepath) as f:
                report = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.summary_label.setText(f"Couldn't read this record: {e}")
            self.stats_table.setRowCount(0)
            self.dirs_label.setPlainText("")
            self.dirs_label.setVisible(False)
            self._all_rows = []
            self.filter_combo.clear()
            self.table.setRowCount(0)
            return

        stats = report.get("file_stats", {})
        self.summary_label.setText("{} ({} total, {} good, {} bad, {} relocated)".format(
            report.get("sojourner_summary", ""),
            stats.get("total", 0), stats.get("good", 0), stats.get("bad", 0), stats.get("relocated", 0)))

        dir_stats = report.get("directory_stats", {})
        missing_dirs = dir_stats.get("missing", [])
        extra_dirs = dir_stats.get("extra", [])
        # One directory per line, not one giant comma-joined run-on string -
        # a real experiment can have dozens of these, and a wall of names
        # separated only by commas is much harder to scan than a list.
        dir_lines = []
        if missing_dirs:
            dir_lines.append(f"Whole subdirectories not on Sojourner at all ({len(missing_dirs)}):")
            dir_lines.extend("  " + d for d in missing_dirs)
        if extra_dirs:
            dir_lines.append(f"Whole subdirectories on Sojourner but not found locally ({len(extra_dirs)}):")
            dir_lines.extend("  " + d for d in extra_dirs)
        self.dirs_label.setPlainText("\n".join(dir_lines))
        self.dirs_label.setVisible(bool(dir_lines))

        # comparison/checksum_results are independent per-path status maps
        # (see compare()/verify_checksums()) - a path can legitimately
        # appear in both if it's e.g. size-matched but checksum-mismatched,
        # so this lists each problem separately rather than trying to
        # collapse them into one row per path.
        comparison = report.get("comparison", {})
        checksum_results = report.get("checksum_results", {})
        relocated_files = report.get("relocated_files", [])

        # A relocated pair's two paths still show up as plain LOCAL_ONLY/
        # REMOTE_ONLY entries in comparison (find_relocated_files never
        # touches compare()'s own output) - skip them here so each gets
        # exactly one row, as the paired "-> " entry below, not also as a
        # separate "missing" entry that would misrepresent it as unexplained.
        relocated_paths = set()
        for rf in relocated_files:
            relocated_paths.add(rf["local_path"])
            relocated_paths.add(rf["remote_path"])

        rows = []  # (path, category_key, issue_label)
        for path, status in comparison.items():
            if status == "MATCH" or path in relocated_paths:
                continue
            rows.append((path, status, self._category_labels.get(status, status)))
        for path, status in checksum_results.items():
            if status in ("CHECKSUM_MATCH", "CHECKSUM_UNKNOWN"):
                continue
            rows.append((path, status, self._category_labels.get(status, status)))
        for rf in relocated_files:
            rows.append(("{} -> {}".format(rf["local_path"], rf["remote_path"]),
                          "RELOCATED", self._relocated_label))
        rows.sort()
        self._all_rows = rows

        # Tabulate: one row per category actually present, in a fixed,
        # good-first/most-common-problem-first order rather than whatever
        # order dict iteration or sorting would give - "Good" is always the
        # first line so the reader doesn't have to hunt for the one number
        # that says "how much of this actually matched".
        category_order = ["GOOD", "LOCAL_ONLY", "REMOTE_ONLY", "RELOCATED",
                           "SIZE_MISMATCH", "CHECKSUM_MISMATCH", "CHECKSUM_ERROR"]
        counts = {"GOOD": stats.get("good", 0)}
        for _, category, _ in rows:
            counts[category] = counts.get(category, 0) + 1
        stats_labels = dict(self._category_labels)
        stats_labels["GOOD"] = "Good (matched)"
        stats_labels["RELOCATED"] = "Relocated"
        present = [c for c in category_order if counts.get(c, 0)]
        present.extend(c for c in counts if c not in category_order and counts[c])
        self.stats_table.setRowCount(len(present))
        for row, category in enumerate(present):
            self.stats_table.setItem(row, 0, QtWidgets.QTableWidgetItem(stats_labels.get(category, category)))
            count_item = QtWidgets.QTableWidgetItem(str(counts[category]))
            count_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.stats_table.setItem(row, 1, count_item)
        self.stats_table.resizeColumnsToContents()

        # Filter dropdown: "All problem files" plus one entry per category
        # actually present in *this* snapshot (not a fixed list) - a
        # snapshot with only missing files shouldn't offer a "Checksum
        # mismatch" choice that's guaranteed to show nothing. Rebuilt (not
        # just repopulated) on every snapshot switch since which categories
        # exist can differ per snapshot; signal is blocked around this so
        # rebuilding doesn't itself trigger a redundant _apply_filter call
        # before self._all_rows above is even meaningful to it.
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem(f"All problem files ({len(rows)})", None)
        problem_categories = [c for c in category_order if c != "GOOD" and counts.get(c, 0)]
        for category in problem_categories:
            self.filter_combo.addItem(f"{stats_labels.get(category, category)} ({counts[category]})", category)
        self.filter_combo.blockSignals(False)

        self._apply_filter()

    def _apply_filter(self):
        selected = self.filter_combo.currentData() if self.filter_combo.count() else None
        rows = self._all_rows if selected is None else [r for r in self._all_rows if r[1] == selected]

        if not rows:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QtWidgets.QTableWidgetItem("(no problem files in this snapshot)"))
            self.table.setItem(0, 1, QtWidgets.QTableWidgetItem(""))
        else:
            self.table.setRowCount(len(rows))
            for row, (path, _category, issue) in enumerate(rows):
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(path))
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(issue))
        self.table.resizeColumnsToContents()
        # Cap the File column rather than leaving resizeColumnsToContents's
        # raw result: a single long real path (confirmed directly - a
        # dozens-of-directories-deep experiment path) can otherwise claim
        # the entire dialog width and push the Issue column off the visible
        # area even with setStretchLastSection(True), since that only
        # controls how leftover space is distributed, not a maximum on
        # earlier columns. Capped, not fixed, so short paths still get a
        # narrow column instead of always reserving 500px.
        if self.table.columnWidth(0) > 500:
            self.table.setColumnWidth(0, 500)


class _ChecksumStopWorker(QtCore.QObject):
    """Requests a clean stop of a running Verify MD5 job, off the GUI
    thread (an SSH round trip, same reason every other remote action here
    runs in a QThread). Just runs `systemctl --user stop <unit>` -
    checksum_worker.py's own SIGTERM handler (see checksum_worker.py's
    _handle_sigterm) does the actual clean shutdown and CANCELLED status
    write; this worker's job ends the moment systemctl confirms the stop
    request was accepted.

    force_status_path/status: when given (only for a job _paint_checksum_
    progress has already flagged as stale - see _CHECKSUM_STALE_SEC), also
    write a CANCELLED status directly after the stop request, regardless
    of whether systemctl's stop actually did anything. A stale job's own
    process is usually already dead - confirmed directly against two real
    jobs stuck at RUNNING for 78h and 20h after their process crashed on a
    since-resolved "no space left on device" error - so its SIGTERM
    handler would never run to write that transition itself, leaving the
    row stuck on "Stop" forever with no way back to Verify MD5 otherwise.

    But staleness alone isn't proof of death: also confirmed directly, a
    job legitimately hashing this beamline's ~30GB-per-file detector data
    over NFS can go many minutes between progress_cb calls (it only
    reports once per whole file, not per chunk) while genuinely still
    alive. If that's what's actually happening, the systemctl stop call
    above is not a no-op - it really does stop the job, same as a normal
    (non-stale) Stop always does; the confirmation dialog in
    _on_stop_checksum says so rather than promising a stale job is
    definitely dead. Not done unconditionally (only when the caller has
    already confirmed staleness): for a job not yet flagged stale, only
    its own SIGTERM-handler write should ever mark it CANCELLED, to avoid
    this worker racing a real in-progress status update.
    """

    done = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)

    def __init__(self, exp_name, host, user, unit_name, force_status_path=None, status=None):
        super().__init__()
        self.exp_name = exp_name
        self.host = host
        self.user = user
        self.unit_name = unit_name
        self.force_status_path = force_status_path
        self.status = status

    def run(self):
        try:
            try:
                di.run_shell_command(self.host, self.user, f"systemctl --user stop {shlex.quote(self.unit_name)}")
            except Exception:
                # Best-effort only when force-clearing a stale job: the
                # unit is expected to already be gone/unknown in that case
                # (that's the whole reason it's stale), so a failure here
                # isn't informative - the force-write below is what
                # actually matters. Re-raised as normal (below) for a
                # non-stale stop, where a systemctl failure IS the answer.
                if self.force_status_path is None:
                    raise
            if self.force_status_path is not None:
                cleared = dict(self.status or {})
                cleared["state"] = "CANCELLED"
                cleared["finished_at"] = time.time()
                cleared["error_message"] = "Force-cleared from the GUI: no progress reported for " \
                    f"{_format_age(time.time() - (self.status or {}).get('updated_at', 0))}."
                di.write_remote_file(self.host, self.user, self.force_status_path, json.dumps(cleared, indent=2))
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))


class _DmUploadWorker(QtCore.QObject):
    """Runs `dm-upload --reprocess` for one experiment, off the GUI thread
    (an SSH round trip to the beamline's designated upload host - see
    dm_integrity.upload_info_for_experiment for why that host differs from
    where DM catalog reads/checksum jobs are routed). This only confirms
    the upload request was accepted by DM - DM's own backend does the
    actual data transfer/cataloging asynchronously from there, the same
    way the beamlines' own dm_end_user_*.sh scripts treat it (fire the
    command, don't wait for the archive to finish ingesting). done carries
    dm-upload's own stdout - the only place the upload/job id DM prints on
    acceptance is available; discarding it left no way to look the upload
    back up in DM afterward."""

    done = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, host, user, setup_script, exp_name, data_directory):
        super().__init__()
        self.host = host
        self.user = user
        self.setup_script = setup_script
        self.exp_name = exp_name
        self.data_directory = data_directory

    def run(self):
        try:
            result = di.run_dm_upload(self.host, self.user, self.setup_script, self.exp_name, self.data_directory)
            self.done.emit(result.stdout or "")
        except Exception as e:
            self.error.emit(str(e))


class AddExperimentDialog(QtWidgets.QDialog):
    """Manually add an experiment to the dashboard that auto-discovery
    didn't pick up - either because it's not among the most-recent
    experiments_per_beamline per beamline, or its name doesn't follow the
    <piname>_<mon><yy> convention discover_local_experiments requires."""

    def __init__(self, parent, beamlines, local_root_templates, local_bases=None, known_names=None):
        super().__init__(parent)
        self.setWindowTitle("Add experiment")
        self._local_root_templates = local_root_templates
        self._local_bases = local_bases or {}
        self._known_names = known_names or set()
        self._path_is_autofilled = True
        self._name_is_autofilled = True

        self.name_edit = QtWidgets.QLineEdit()
        self.beamline_combo = QtWidgets.QComboBox()
        self.beamline_combo.addItems(beamlines)

        self.path_edit = QtWidgets.QLineEdit()
        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        path_row = QtWidgets.QHBoxLayout()
        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse_btn)

        form = QtWidgets.QFormLayout()
        form.addRow("Experiment name:", self.name_edit)
        form.addRow("Beamline:", self.beamline_combo)
        form.addRow("Local folder:", path_row)

        self.warning_label = QtWidgets.QLabel("")
        self.warning_label.setStyleSheet("color: red;")

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.warning_label)
        layout.addWidget(buttons)

        # Pre-fill the local folder from the beamline's convention template
        # as the name/beamline are entered, so the common case (a real
        # convention-named experiment that's just older than the
        # most-recent few) needs no manual path entry at all - but never
        # clobber something the user actually typed or Browsed to.
        self.name_edit.textChanged.connect(self._maybe_autofill_path)
        self.name_edit.textEdited.connect(self._on_name_edited_by_user)
        self.beamline_combo.currentTextChanged.connect(self._maybe_autofill_path)
        self.path_edit.textEdited.connect(self._on_path_edited_by_user)
        self.name_edit.textChanged.connect(self._validate)
        self._validate()

    def _on_path_edited_by_user(self):
        self._path_is_autofilled = False

    def _on_name_edited_by_user(self):
        self._name_is_autofilled = False

    def _maybe_autofill_path(self):
        if not self._path_is_autofilled:
            return
        name = self.name_edit.text().strip()
        template = self._local_root_templates.get(self.beamline_combo.currentText())
        if name and template:
            self.path_edit.setText(di.canonical_local_root(template.format(expid=name)))
            self._path_is_autofilled = True  # setText() doesn't emit textEdited, but stay explicit

    def _validate(self):
        name = self.name_edit.text().strip()
        if name and name in self._known_names:
            self.warning_label.setText(f"'{name}' is already tracked - pick a different name.")
            self._ok_button.setEnabled(False)
        else:
            self.warning_label.setText("")
            self._ok_button.setEnabled(True)

    def _browse(self):
        # Start from the currently selected beamline's own base directory
        # (e.g. ~/mnt/s1c) rather than the home directory, so browsing to a
        # real experiment folder is a couple of clicks, not a manual cd
        # through unrelated home-directory clutter.
        start_dir = self.path_edit.text().strip()
        if not start_dir:
            base = self._local_bases.get(self.beamline_combo.currentText())
            start_dir = di.canonical_local_root(base) if base else os.path.expanduser("~")
        path = _choose_directory(self, "Select experiment folder", start_dir)
        if not path:
            return
        self.path_edit.setText(path)
        self._path_is_autofilled = False

        # Picking a folder is the common "I already know where it is"
        # path - populate the experiment name from its directory name so
        # the user isn't forced to retype what they just navigated to.
        # Never clobber a name the user typed themselves first.
        if self._name_is_autofilled:
            self.name_edit.setText(os.path.basename(path.rstrip("/")))
            self._name_is_autofilled = True  # setText() doesn't emit textEdited, but stay explicit

        # Infer the beamline too, if the chosen folder falls under one of
        # the known local_bases (e.g. picking something under ~/mnt/s20a
        # while "s1" is still selected from a prior add) - reuses
        # di.beamline_for_path rather than a second, separately-maintained
        # copy of this inference. Confirmed directly that a naive string-
        # prefix version of this check (what used to be here inline) can
        # silently fail to infer anything: the same underlying storage was
        # reachable through two different real mount paths (different
        # strings even after realpath, same device+inode) - see
        # beamline_for_path's own docstring for the full story.
        inferred = di.beamline_for_path(self._local_bases, path)
        if inferred is not None:
            index = self.beamline_combo.findText(inferred)
            if index >= 0:
                self.beamline_combo.setCurrentIndex(index)

    def values(self):
        """(name, beamline, path) - path is whatever's in the field, not
        yet canonicalized (the caller does that, same as everywhere else
        a local_root gets written into config or a job spec)."""
        return self.name_edit.text().strip(), self.beamline_combo.currentText(), self.path_edit.text().strip()


class DataIntegrityPanel(QtWidgets.QWidget):
    def __init__(self, config_path, show_font_control=True):
        super().__init__()
        self.config_path = config_path
        self.config = {}
        self.show_font_control = show_font_control
        self.font_size = 10
        self.last_reports = {}
        self._row_buttons = {}
        self._row_upload_buttons = {}
        self._row_history_labels = {}
        self._upload_workers = {}
        self._active_workers = {}
        # Detached checksum jobs (Verify MD5): _tracked_checksum_jobs holds
        # the last-known status dict per experiment, refreshed by the poll
        # timer from the beamline's shared status file (plain local reads -
        # no SSH). _checksum_launch_workers keeps launch-in-progress
        # QThread/worker pairs alive, same reason _active_workers does.
        # _checksum_stop_workers is the same idea for an in-flight Stop
        # request (see _on_stop_checksum).
        self._tracked_checksum_jobs = {}
        self._checksum_launch_workers = {}
        self._checksum_stop_workers = {}

        self._load_config()
        self._init_ui()

        # Auto-discover and populate experiments on startup
        self._discover_and_populate_experiments()

        poll_interval_ms = int(self.config.get("settings", {}).get("checksum_poll_interval_sec", 4) * 1000)
        self._checksum_poll_timer = QtCore.QTimer(self)
        self._checksum_poll_timer.timeout.connect(self._poll_checksum_jobs)
        self._checksum_poll_timer.start(poll_interval_ms)

    def _discover_and_populate_experiments(self):
        """Find recent experiments by looking directly at the s1c/s20a local
        staging directories, instead of querying DM/Sojourner.

        This sidesteps a real mess we ran into with the Sojourner-based
        approach: upload-record timestamps don't reliably reflect experiment
        recency (a re-upload of old data can outrank a brand-new one), an
        experiment with no upload yet doesn't show up at all even though
        it's exactly the "currently active" case you'd want to see, and it
        needed SSH + picking the right DM VM to even ask the question. A
        directory's mtime under s1c/s20a is a much more direct signal of
        "this is currently being worked on," requires no network access at
        all, and - since it *is* local_root - it also means Scan/Verify
        never need to guess/prompt for a path for these rows.
        """
        if di is None:
            return

        settings = self.config.get("settings", {})
        local_bases = settings.get("local_bases", {
            "s1": "~/mnt/s1c",
            "s20": "~/mnt/s20a",
        })
        per_beamline = settings.get("experiments_per_beamline", 3)

        try:
            # Dict order (s1 before s20, per the config file) gives us
            # "grouped by sector" for free; discover_local_experiments
            # already sorts each beamline's own results by recency.
            # local_bases is ~-relative so the same config works whether
            # this GUI is launched as parkjs, S1IDUSER, or S20IDUSER (all
            # three resolve ~/mnt/s1c and ~/mnt/s20a to the same canonical
            # /home/s1c, /home/s20a - confirmed directly) - canonicalize
            # before use, since discover_local_experiments itself just
            # does plain os.path calls with no ~ expansion of its own.
            recent_exps = []
            for beamline, base_dir in local_bases.items():
                canonical_base = di.canonical_local_root(base_dir)
                for exp_name, local_root in di.discover_local_experiments(canonical_base, limit=per_beamline):
                    recent_exps.append((exp_name, beamline, local_root))
                    self._register_local_root(exp_name, local_root)

            manual_exps = self._load_manual_experiments({name for name, _, _ in recent_exps})
            manual_names = {name for name, _, _ in manual_exps}
            all_exps = recent_exps + manual_exps

            if not all_exps:
                self._log("No experiment directories found under " + ", ".join(local_bases.values()))
                return

            self._ensure_six_column_layout()
            self.table_widget.setRowCount(len(all_exps))
            self._row_buttons = {}
            self._row_upload_buttons = {}
            self._row_history_labels = {}

            for row, (exp_name, beamline, local_root) in enumerate(all_exps):
                self._populate_experiment_row(row, exp_name, beamline, is_manual=exp_name in manual_names)

            # Size columns to their actual content (header text + cell
            # widgets, e.g. the Scan/Verify MD5 buttons) at the current
            # font, instead of hardcoded pixel widths that clip/truncate as
            # soon as the font size changes from whatever they were tuned
            # for.
            self.table_widget.resizeColumnsToContents()
            self.table_widget.resizeRowsToContents()

            self._reattach_checksum_jobs(all_exps)
            self._recompute_aggregate_summary()

            counts = {}
            for _, beamline, _ in all_exps:
                counts[beamline] = counts.get(beamline, 0) + 1
            summary = ", ".join(f"{n} from {b}" for b, n in counts.items())
            extra = f" + {len(manual_exps)} manually added" if manual_exps else ""
            self._log(f"Loaded {summary}{extra} (from local s1c/s20a directories)")

        except Exception as e:
            self._log(f"Error discovering experiments: {str(e)[:100]}")

    def _ensure_six_column_layout(self):
        """Switch to the full 7-column layout (adds Beamline, History, and
        DM Upload) - the base table from _init_ui only has 5 columns, and
        setHorizontalHeaderLabels does NOT grow columnCount on its own, so
        without this the extra columns (Actions sliding to column 4,
        History needing column 5, DM Upload needing column 6) would
        silently never appear. A no-op once already at 7 columns - needed
        both by bulk discovery and by add_experiment(), since a manual add
        can be the very first row (e.g. local_bases found nothing, so bulk
        discovery never got past the 5-column table _init_ui starts
        with)."""
        if self.table_widget.columnCount() >= 7:
            return
        self.table_widget.setColumnCount(7)
        self.table_widget.setHorizontalHeaderLabels([
            "Expid", "Beamline", "Upload Status", "Files", "Actions", "History", "DM Upload"
        ])

    def _load_manual_experiments(self, existing_names):
        """Experiments explicitly added via "Add experiment..." - persisted
        to the config's "experiments" list with an explicit "beamline" key,
        which is what distinguishes a manually-tracked entry from the
        in-memory-only local_root cache _register_local_root maintains for
        auto-discovered ones (never has "beamline" set, never written to
        disk). Skips anything already covered by auto-discovery, and
        anything whose local_root no longer resolves to a real directory
        (data may have moved or been cleaned up since it was added).
        """
        manual = []
        for exp in self.config.get("experiments", []):
            name = exp.get("name")
            beamline = exp.get("beamline")
            local_root = exp.get("local_root")
            if not name or not beamline or not local_root or name in existing_names:
                continue
            if not os.path.isdir(local_root):
                continue
            manual.append((name, beamline, local_root))
        return manual

    def _populate_experiment_row(self, row, exp_name, beamline, is_manual=False):
        """Fill in an already-row-counted table row's cells/widgets for
        exp_name - shared by the bulk startup population above and
        _append_experiment_row (a single new row added via "Add
        experiment..." without rebuilding the whole table). is_manual
        controls whether a "Remove" button is shown - only meaningful for
        manually-added rows, since removing an auto-discovered one would
        have no lasting effect (it just reappears next discovery)."""
        # Expid
        exp_id_item = QtWidgets.QTableWidgetItem(exp_name)
        self.table_widget.setItem(row, 0, exp_id_item)

        # Beamline (s1 or s20)
        beamline_item = QtWidgets.QTableWidgetItem(beamline)
        self.table_widget.setItem(row, 1, beamline_item)

        # Upload status
        upload_status_item = QtWidgets.QTableWidgetItem("---")
        self.table_widget.setItem(row, 2, upload_status_item)

        # Files
        files_item = QtWidgets.QTableWidgetItem("---")
        self.table_widget.setItem(row, 3, files_item)

        # Actions
        buttons_layout = QtWidgets.QHBoxLayout()
        scan_btn = QtWidgets.QPushButton("Scan")
        scan_btn.clicked.connect(lambda checked, e=exp_name: self._on_scan(e))
        # One button, not two swapped by visibility: it reads "Verify MD5"
        # normally and "Stop" while a checksum job is tracked as QUEUED/
        # RUNNING (see _set_checksum_running_ui), dispatching to whichever
        # action is currently live. A single widget whose label/handler
        # change removes any chance of the two states laying out
        # differently - confirmed the earlier two-button-with-visibility-
        # toggle approach could still visibly misalign row-to-row.
        verify_btn = QtWidgets.QPushButton("Verify MD5")
        verify_btn.clicked.connect(lambda checked, e=exp_name: self._on_verify_or_stop(e))
        buttons_layout.addWidget(scan_btn)
        buttons_layout.addWidget(verify_btn)
        if is_manual:
            remove_btn = QtWidgets.QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked, e=exp_name: self._on_remove_experiment(e))
            buttons_layout.addWidget(remove_btn)
        # Compact "N recs" indicator for exp_name's saved Scan/Verify MD5
        # history, filling what would otherwise be dead space between the
        # buttons and the trailing stretch (see below) whenever a row's
        # buttons are narrower than the widest row in the column. Purely
        # informational (not clickable) - History still opens the detail
        # dialog; this just makes "does history even exist for this row"
        # visible without a click. Refreshed at population time and again
        # whenever a fresh report is painted (_paint_experiment_row).
        history_summary_label = QtWidgets.QLabel("")
        buttons_layout.addWidget(history_summary_label)
        self._row_history_labels[exp_name] = history_summary_label
        self._row_buttons[exp_name] = (scan_btn, verify_btn)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        # Without a trailing stretch, a QHBoxLayout with only Minimum-size-
        # policy widgets (QPushButton's default) grows them to fill
        # whatever width the cell ends up with - which is sized to the
        # widest row in the whole column (e.g. one with "Verify MD5" +
        # "Remove"), so a row with the shorter "Scan"/"Stop" pair stretched
        # its own buttons wider to match instead of just leaving the gap
        # unused. Confirmed directly: this is what made Scan/Verify-MD5/
        # Stop buttons visibly misaligned row-to-row. The stretch absorbs
        # the leftover space instead, so every row's buttons keep their
        # natural size and line up from the left consistently.
        buttons_layout.addStretch()

        buttons_widget = QtWidgets.QWidget()
        buttons_widget.setLayout(buttons_layout)
        self.table_widget.setCellWidget(row, 4, buttons_widget)

        # History
        history_btn = QtWidgets.QPushButton("History")
        history_btn.clicked.connect(lambda checked, e=exp_name: self._on_history(e))
        self.table_widget.setCellWidget(row, 5, history_btn)

        # DM Upload - pushes local_root's data into Sojourner via
        # `dm-upload --reprocess` (see _on_upload_to_dm). Kept as its own
        # column rather than folded into Actions: unlike Scan/Verify MD5/
        # Stop (all read-only or self-contained), this writes into shared
        # production infrastructure, so it gets its own confirmation flow
        # and shouldn't be visually lumped in with the routine buttons.
        upload_btn = QtWidgets.QPushButton("Upload to DM")
        upload_btn.clicked.connect(lambda checked, e=exp_name: self._on_upload_to_dm(e))
        self._row_upload_buttons[exp_name] = upload_btn
        self.table_widget.setCellWidget(row, 6, upload_btn)

        # Deliberately NOT previewing DM status here: local_root is
        # already known (that's the point of local discovery / the
        # explicit path from "Add experiment..."), so an automatic
        # preview would mean a real DM/SSH check for every row on every
        # startup. Checking against DM is Scan/Verify MD5's job -
        # explicit, on-demand, backgrounded. The history summary label
        # IS populated now, though - it's plain local file reads (see
        # _history_summary), no network/SSH cost at all.
        self._refresh_history_summary(exp_name, beamline)

    def _history_summary(self, exp_name, beamline):
        """(indicator_text, tooltip_text) for exp_name's saved Scan/Verify
        MD5 records - same records _on_history's dialog reads (checks both
        the beamline's shared checksum records dir and the legacy flat
        settings.records_dir), just reduced to a glance-able count/last-
        result instead of the full drill-down. Local file reads only
        (di.list_records), same cost class as _reattach_checksum_jobs'
        status-file reads - cheap enough to call for every row.
        """
        if di is None:
            return "", ""

        records_dirs = []
        if beamline:
            _, _, remote_base = di.remote_identity_for_beamline(self.config, beamline)
            if remote_base:
                records_dirs.append(di.checksum_records_dir(remote_base))
        legacy_records_dir = self.config.get("settings", {}).get("records_dir", di.DEFAULT_RECORDS_DIR)
        if legacy_records_dir not in records_dirs:
            records_dirs.append(legacy_records_dir)

        records = []
        for records_dir in records_dirs:
            records.extend(di.list_records(records_dir, exp_name))
        if not records:
            return "", "No saved Scan/Verify MD5 records yet."

        records.sort(key=lambda r: r[0])
        timestamp, filepath = records[-1]
        try:
            with open(filepath) as f:
                report = json.load(f)
            stats = report.get("file_stats", {})
            last_result = "{} good / {} bad".format(stats.get("good", 0), stats.get("bad", 0))
        except (OSError, json.JSONDecodeError):
            last_result = "last record unreadable"

        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
        n = len(records)
        text = "{} rec{}".format(n, "" if n == 1 else "s")
        tooltip = "{} saved record{} - last checked {}: {}".format(n, "" if n == 1 else "s", when, last_result)
        return text, tooltip

    def _refresh_history_summary(self, exp_name, beamline):
        label = self._row_history_labels.get(exp_name)
        if not label:
            return
        text, tooltip = self._history_summary(exp_name, beamline)
        label.setText(text)
        label.setToolTip(tooltip)

    def _append_experiment_row(self, exp_name, beamline, is_manual=False):
        """Add exp_name as one new row at the end of the table, without
        rebuilding/rescanning everything else - used by add_experiment()
        so adding one manually-tracked experiment doesn't re-trigger a
        full directory rediscovery."""
        self._ensure_six_column_layout()
        row = self.table_widget.rowCount()
        self.table_widget.setRowCount(row + 1)
        self._populate_experiment_row(row, exp_name, beamline, is_manual=is_manual)
        self.table_widget.resizeColumnsToContents()
        self.table_widget.resizeRowsToContents()
        return row

    def add_experiment(self):
        """Manually add an experiment via AddExperimentDialog - for one
        that auto-discovery didn't surface (older than the most-recent few
        per beamline, or named outside the <piname>_<mon><yy> convention).
        Persisted to config's "experiments" list with an explicit
        "beamline" key (see _load_manual_experiments), so it reappears on
        every future startup, not just this session.
        """
        if di is None:
            _message_box(QtWidgets.QMessageBox.Warning, self, "Unavailable", "dm_integrity module not available.")
            return

        settings = self.config.get("settings", {})
        local_bases = settings.get("local_bases", {"s1": None, "s20": None})
        beamlines = list(local_bases.keys())
        templates = settings.get("local_root_templates", {})
        known_names = {
            self.table_widget.item(row, 0).text()
            for row in range(self.table_widget.rowCount())
            if self.table_widget.item(row, 0)
        }

        # Logged unconditionally before attempting to open, and the whole
        # attempt wrapped in try/except reporting through self._log - see
        # _on_history's identical treatment for why: this makes "click not
        # received" / "exception while opening" / "dialog created but
        # never mapped by the X server" distinguishable from the user's
        # side, where before they all looked identical (nothing visible,
        # nothing in the terminal).
        self._log("Opening Add EXPID...")
        try:
            dialog = AddExperimentDialog(self, beamlines, templates, local_bases=local_bases, known_names=known_names)
            _center_on_parent(dialog, self)
            accepted = dialog.exec_() == QtWidgets.QDialog.Accepted
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._log(f"Failed to open Add EXPID: {e}")
            return
        if not accepted:
            return

        name, beamline, path = dialog.values()
        if not name or not path:
            _message_box(QtWidgets.QMessageBox.Warning, self, "Missing info", "Experiment name and local folder are both required.")
            return
        if self._row_for_exp(name) is not None:
            # Belt-and-suspenders: the dialog itself already disables OK
            # for a name in known_names, but re-check here too in case the
            # table changed while the (modal) dialog was open, or a caller
            # ever invokes this without going through the dialog's guard.
            _message_box(QtWidgets.QMessageBox.Warning, self, "Already added", f"'{name}' is already in the table.")
            return

        canonical_path = di.canonical_local_root(path)
        if not os.path.isdir(canonical_path):
            _message_box(QtWidgets.QMessageBox.Warning, self, "Not found", f"'{canonical_path}' is not a directory.")
            return

        # Read-modify-write the config file directly, rather than dumping
        # self.config as a whole: _register_local_root appends in-memory-
        # only entries (no "beamline" key) to self.config["experiments"]
        # for auto-discovered rows, which must never be written to disk -
        # see _load_manual_experiments/_register_local_root.
        on_disk = {}
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                on_disk = json.load(f)
        experiments = [e for e in on_disk.get("experiments", []) if e.get("name") != name]
        experiments.append({"name": name, "beamline": beamline, "local_root": canonical_path, "dataset": None})
        on_disk["experiments"] = experiments
        di.save_config(on_disk, self.config_path)

        # Mirror the same entry into the in-memory config so
        # _resolve_local_root/_load_manual_experiments see it immediately
        # without needing a restart.
        self.config["experiments"] = [
            e for e in self.config.get("experiments", []) if e.get("name") != name
        ] + [{"name": name, "beamline": beamline, "local_root": canonical_path, "dataset": None}]

        self._append_experiment_row(name, beamline, is_manual=True)
        self._reattach_checksum_jobs([(name, beamline, canonical_path)])
        self._recompute_aggregate_summary()
        self._log(f"Added experiment '{name}' ({beamline})")

    def _on_remove_experiment(self, exp_name):
        """Remove a manually-added row (see add_experiment) from both the
        table and the config file. Only ever wired up for is_manual rows -
        removing an auto-discovered row wouldn't stick anyway, since the
        next _discover_and_populate_experiments would just find it again.
        """
        if (exp_name in self._tracked_checksum_jobs or exp_name in self._checksum_launch_workers
                or exp_name in self._active_workers):
            _message_box(
                QtWidgets.QMessageBox.Warning, self, "Busy",
                f"'{exp_name}' has a Scan or Verify MD5 in progress - stop it first.")
            return

        reply = _message_box(
            QtWidgets.QMessageBox.Question, self, "Remove experiment",
            f"Remove '{exp_name}' from the dashboard?\n\nThis only forgets it here - no local files or "
            "Sojourner data are touched.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes:
            return

        if di is not None and os.path.exists(self.config_path):
            with open(self.config_path) as f:
                on_disk = json.load(f)
            on_disk["experiments"] = [
                e for e in on_disk.get("experiments", [])
                if not (e.get("name") == exp_name and e.get("beamline"))
            ]
            di.save_config(on_disk, self.config_path)

        self.config["experiments"] = [
            e for e in self.config.get("experiments", [])
            if not (e.get("name") == exp_name and e.get("beamline"))
        ]

        row = self._row_for_exp(exp_name)
        if row is not None:
            self.table_widget.removeRow(row)
        self._row_buttons.pop(exp_name, None)
        self._row_upload_buttons.pop(exp_name, None)
        self._row_history_labels.pop(exp_name, None)
        self.last_reports.pop(exp_name, None)

        self._recompute_aggregate_summary()
        self._log(f"Removed experiment '{exp_name}'")

    def _on_upload_to_dm(self, exp_name):
        """Trigger `dm-upload --reprocess` for exp_name, to push local
        files into Sojourner and resolve a discrepancy a Scan/Verify MD5
        found (missing files, size mismatches, etc.) - the same command
        the beamlines' own end-of-experiment scripts run, just without the
        DAQ-stop/detector-rsync/metadata-copy steps around it, which are
        experiment-teardown-specific and out of scope for "fix Sojourner".
        Unlike Scan/Verify MD5 (read-only) or Stop (only affects a job this
        tool itself launched), this writes into shared production
        infrastructure - hence the confirmation dialog spelling out the
        exact command before it runs, rather than firing immediately.
        """
        if di is None:
            return

        beamline = self._beamline_for_exp(exp_name)
        host, user, setup_script, data_directory = di.upload_info_for_experiment(self.config, beamline, exp_name)
        if not host or not data_directory:
            _message_box(
                QtWidgets.QMessageBox.Warning, self, "Not configured",
                f"No upload_hosts/local_bases entry configured for beamline '{beamline}' - can't determine "
                "where to run dm-upload from or what data-directory to pass it.")
            return

        command_line = di.dm_upload_command(exp_name, data_directory)
        reply = _message_box(
            QtWidgets.QMessageBox.Question, self, "Upload to DM",
            f"This pushes '{exp_name}' into Sojourner via DM, running as {user}@{host}:\n\n"
            f"  {command_line}\n\n"
            "This writes into the shared production archive and can't be undone from here. Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes:
            return

        upload_btn = self._row_upload_buttons.get(exp_name)
        if upload_btn:
            upload_btn.setEnabled(False)
        self._log(f"Uploading '{exp_name}' to DM (running in background)...")

        thread = QtCore.QThread(self)
        worker = _DmUploadWorker(host, user, setup_script, exp_name, data_directory)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(lambda output: self._on_upload_done(exp_name, output))
        worker.error.connect(lambda msg: self._on_upload_error(exp_name, msg))
        worker.done.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._upload_workers[exp_name] = (thread, worker)
        thread.start()

    def _on_upload_done(self, exp_name, output):
        """dm-upload prints an upload/job id on acceptance - shown here
        (not just a generic "triggered" message) since that's the only
        record of it; DM doesn't surface it anywhere else this tool
        already queries. get_upload_status (what Scan/Verify MD5's
        "Upload Status"/"Files" columns already show) is the way to check
        progress afterward - no separate polling added here since that
        path already exists."""
        self._upload_workers.pop(exp_name, None)
        upload_btn = self._row_upload_buttons.get(exp_name)
        if upload_btn:
            upload_btn.setEnabled(True)
        output = output.strip()
        self._log(
            f"Upload triggered for '{exp_name}'. dm-upload output: {output or '(none)'} - "
            "re-run Scan/Verify MD5 in a bit to see it reflected in Upload Status/Files.")
        _message_box(
            QtWidgets.QMessageBox.Information, self, "Upload triggered",
            f"dm-upload accepted the request for '{exp_name}'.\n\n"
            f"Output:\n{output or '(dm-upload produced no output)'}\n\n"
            "To check progress: re-run Scan or Verify MD5 for this row in a bit - both already "
            "query DM's own upload status (the same listUploadRecords lookup DM's job id would "
            "point at) and refresh the Upload Status/Files columns from it.")

    def _on_upload_error(self, exp_name, msg):
        self._upload_workers.pop(exp_name, None)
        upload_btn = self._row_upload_buttons.get(exp_name)
        if upload_btn:
            upload_btn.setEnabled(True)
        # dm-upload's own exit-15 message for this case ("Upload id ... is
        # already active or pending for experiment ...") - confirmed
        # directly against DM Station's own Uploads tab: this isn't a
        # failure at all, it's DM correctly refusing a second concurrent
        # reprocess while an earlier one (often from a prior click here) is
        # still genuinely running. Logged distinctly so it doesn't read
        # like something to retry or debug - Scan/Verify MD5 (not another
        # Upload to DM click) or DM Station's Uploads tab is what actually
        # shows its progress.
        if "already active or pending" in msg:
            self._log(
                f"'{exp_name}' already has an upload in progress on DM (not a failure) - "
                "check DM Station's Uploads tab for progress, or re-run Scan/Verify MD5 here "
                "once it finishes.")
            return
        # dm-upload's own exit-16 message ("Experiment ... is already
        # archived") - confirmed directly for a real experiment: DM refuses
        # --reprocess entirely once an experiment has been archived, by
        # design, not a transient failure. Nothing to retry here - if
        # Sojourner is genuinely missing/mismatched files for an archived
        # experiment, DM Upload from this tool can't fix it; that needs
        # DM's own un-archive/restore path (outside this tool's scope).
        if "already archived" in msg:
            self._log(
                f"'{exp_name}' is already archived in DM - archived experiments can't be "
                "re-uploaded/reprocessed from here. If Sojourner is still missing files for it, "
                "that needs DM's own un-archive process, not another Upload to DM attempt.")
            return
        self._log(f"Upload failed for '{exp_name}': {msg}")

    def _row_for_exp(self, exp_name):
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 0)
            if item and item.text() == exp_name:
                return row
        return None

    def _all_checksum_status_dirs(self):
        """status_dir for every configured beamline - used both for the
        job spec (so checksum_worker.py's CPU governor can count peers
        across beamlines) and, here in the GUI, to know where to look when
        reattaching/polling."""
        hosts = self.config.get("settings", {}).get("checksum_hosts", {})
        return [di.checksum_status_dir(entry["remote_base"]) for entry in hosts.values() if entry.get("remote_base")]

    def _reattach_checksum_jobs(self, recent_exps):
        """For every row just populated, check whether a checksum job is
        already QUEUED/RUNNING for that experiment - a plain local read of
        its beamline's shared status file (world-readable homes, confirmed;
        no SSH needed). This is the entire reattachment mechanism: a job
        launched from a GUI that's since been closed, or from a colleague's
        own GUI instance, shows up here exactly the same way.
        """
        if di is None:
            return
        checksum_hosts = self.config.get("settings", {}).get("checksum_hosts", {})
        for exp_name, beamline, _local_root in recent_exps:
            entry = checksum_hosts.get(beamline)
            if not entry or not entry.get("remote_base"):
                continue
            status_path = di.checksum_status_path(entry["remote_base"], exp_name)
            try:
                with open(status_path) as f:
                    status = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            if status.get("state") in _CHECKSUM_TERMINAL_STATES:
                continue

            self._tracked_checksum_jobs[exp_name] = status
            self._set_checksum_running_ui(exp_name, True)
            row = self._row_for_exp(exp_name)
            if row is not None:
                self._paint_checksum_progress(row, status)

    def _poll_checksum_jobs(self):
        """Re-read every tracked experiment's status file (plain local
        I/O - safe to run directly on the GUI thread every tick, no QThread
        needed) and repaint. On reaching a terminal state, load the full
        saved report (the status file only carries summary counters) and
        hand off to _paint_experiment_row, exactly the same finished-row
        rendering Scan uses."""
        if di is None or not self._tracked_checksum_jobs:
            return

        checksum_hosts = self.config.get("settings", {}).get("checksum_hosts", {})
        for exp_name in list(self._tracked_checksum_jobs.keys()):
            beamline = self._beamline_for_exp(exp_name)
            entry = checksum_hosts.get(beamline)
            if not entry or not entry.get("remote_base"):
                continue
            status_path = di.checksum_status_path(entry["remote_base"], exp_name)
            try:
                with open(status_path) as f:
                    status = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            row = self._row_for_exp(exp_name)
            state = status.get("state")

            if state not in _CHECKSUM_TERMINAL_STATES:
                self._tracked_checksum_jobs[exp_name] = status
                if row is not None:
                    self._paint_checksum_progress(row, status)
                continue

            # Terminal - stop tracking and swap Stop back for Verify MD5
            # regardless of outcome (DONE, FAILED, or CANCELLED via Stop).
            del self._tracked_checksum_jobs[exp_name]
            self._set_checksum_running_ui(exp_name, False)

            if state == "DONE" and status.get("report_path"):
                try:
                    with open(status["report_path"]) as f:
                        report = json.load(f)
                    self.last_reports[exp_name] = report
                    if row is not None:
                        self._paint_experiment_row(row, report)
                    file_stats = report["file_stats"]
                    msg = (f"Checksum verification complete for '{exp_name}': {report['sojourner_summary']} "
                           f"({file_stats['good']} good / {file_stats['bad']} bad)")
                    if report["recommend_deletion"]:
                        msg += " - SAFE TO DELETE"
                    self._log(msg)
                except (OSError, json.JSONDecodeError) as e:
                    self._log(f"Checksum job for '{exp_name}' finished but its report couldn't be read: {e}")
            elif state == "FAILED":
                self._log(f"Checksum verification failed for '{exp_name}': {status.get('error_message', 'unknown error')}")
            elif state == "CANCELLED":
                self._log(f"Checksum verification for '{exp_name}' was cancelled")

    def _paint_checksum_progress(self, row, status):
        six_col = self.table_widget.columnCount() >= 6
        status_col, files_col = (2, 3) if six_col else (1, 2)

        state = status.get("state", "QUEUED")
        age = time.time() - status.get("updated_at", 0)
        stale = state == "RUNNING" and age > _CHECKSUM_STALE_SEC
        label = "Queued" if state == "QUEUED" else ("Stalled?" if stale else "Verifying")
        status_item = QtWidgets.QTableWidgetItem(label)
        if stale:
            status_item.setToolTip(
                f"No progress reported in {_format_age(age)}. Likely dead (crashed, killed, host "
                "issue) - but a single very large file can also legitimately take this long to "
                "hash with no progress update in between, so check before assuming it's stuck. "
                "If it really is dead, use Stop to force-clear it and re-run Verify MD5.")
        self.table_widget.setItem(row, status_col, status_item)

        total = status.get("total_files", 0)
        checked = status.get("checked_files", 0)
        pct = int(100 * checked / total) if total else 0
        color = STATUS_COLORS["stale"] if stale else STATUS_COLORS["in_progress"]
        files_item = QtWidgets.QTableWidgetItem(f"{checked}/{total} checked ({pct}%)")
        files_item.setBackground(color)
        self.table_widget.setItem(row, files_col, files_item)

        for col in range(files_col + 1):
            cell = self.table_widget.item(row, col)
            if cell:
                cell.setBackground(color)

    def _set_verify_button_enabled(self, exp_name, enabled):
        buttons = self._row_buttons.get(exp_name)
        if buttons:
            buttons[1].setEnabled(enabled)

    def _set_checksum_running_ui(self, exp_name, running):
        """Relabel the Verify MD5/Stop button (one widget, not two swapped
        by visibility - see _populate_experiment_row) once a checksum job
        is confirmed tracked as QUEUED/RUNNING - called from
        _reattach_checksum_jobs, _on_checksum_launched, and
        _poll_checksum_jobs' terminal branch. Deliberately separate from
        _set_verify_button_enabled, which _launch_checksum_job still uses
        on its own during the brief pre-launch window (nothing to stop yet
        - no unit_name exists until the launch actually succeeds)."""
        buttons = self._row_buttons.get(exp_name)
        if not buttons:
            return
        _, verify_btn = buttons
        verify_btn.setText("Stop" if running else "Verify MD5")
        verify_btn.setEnabled(True)

    def _on_verify_or_stop(self, exp_name):
        """Dispatch the combined Verify MD5/Stop button click to whichever
        action its current label represents."""
        if exp_name in self._tracked_checksum_jobs:
            self._on_stop_checksum(exp_name)
        else:
            self._on_verify_md5(exp_name)

    def _on_stop_checksum(self, exp_name):
        """Ask for confirmation, then request a clean stop of exp_name's
        running checksum job via `systemctl --user stop <unit>` over SSH -
        checksum_worker.py's own SIGTERM handler (see checksum_worker.py's
        _handle_sigterm) turns that into a CANCELLED status write, which
        the next _poll_checksum_jobs tick picks up exactly like any other
        terminal transition. No progress is saved/resumed - a future
        Verify MD5 run for this experiment starts over from scratch.

        If the tracked status is already stale (see _CHECKSUM_STALE_SEC/
        _paint_checksum_progress), the job's own process is presumed dead
        and won't ever write that CANCELLED transition itself - the
        confirmation dialog says so, and _ChecksumStopWorker is told to
        force-write it directly instead of waiting for a SIGTERM handler
        that will never run."""
        if di is None:
            return

        beamline = self._beamline_for_exp(exp_name)
        checksum_host, checksum_user, remote_base = di.remote_identity_for_beamline(self.config, beamline)
        if not checksum_host:
            self._log(f"Can't stop '{exp_name}': no checksum host configured for beamline '{beamline}'")
            return

        status = self._tracked_checksum_jobs.get(exp_name) or {}
        unit_name = status.get("unit_name") or di.checksum_unit_name(exp_name)
        age = time.time() - status.get("updated_at", 0)
        stale = status.get("state") == "RUNNING" and age > _CHECKSUM_STALE_SEC

        if stale:
            reply = _message_box(
                QtWidgets.QMessageBox.Question, self, "Force-clear stalled verification",
                f"'{exp_name}' hasn't reported progress in {_format_age(age)} - likely dead (crashed, "
                "killed, host issue), but an exceptionally large file can occasionally take this long "
                "to hash with no update in between.\n\n"
                "Force-clear it so you can start a fresh Verify MD5? If it turns out to still be "
                "alive, this stops it (same tradeoff as a normal Stop: progress on this run isn't "
                "saved either way).",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        else:
            reply = _message_box(
                QtWidgets.QMessageBox.Question, self, "Stop verification",
                f"Stop the running MD5 verification for '{exp_name}'?\n\n"
                "Progress isn't saved - a future Verify MD5 run starts over from the beginning.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes:
            return

        buttons = self._row_buttons.get(exp_name)
        if buttons:
            buttons[1].setEnabled(False)  # avoid double-firing while the stop request is in flight
        self._log(f"{'Force-clearing stalled' if stale else 'Stopping'} verification for '{exp_name}'...")

        force_status_path = di.checksum_status_path(remote_base, exp_name) if stale and remote_base else None
        thread = QtCore.QThread(self)
        worker = _ChecksumStopWorker(exp_name, checksum_host, checksum_user, unit_name,
                                      force_status_path=force_status_path, status=status)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(lambda: self._on_stop_checksum_done(exp_name))
        worker.error.connect(lambda msg: self._on_stop_checksum_error(exp_name, msg))
        worker.done.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._checksum_stop_workers[exp_name] = (thread, worker)
        thread.start()

    def _on_stop_checksum_done(self, exp_name):
        self._checksum_stop_workers.pop(exp_name, None)
        self._log(f"Stop requested for '{exp_name}' - the row will update once it's confirmed cancelled.")
        # Deliberately leave _tracked_checksum_jobs/button state alone here:
        # the next _poll_checksum_jobs tick reads the CANCELLED status
        # checksum_worker.py's SIGTERM handler writes and does the normal
        # terminal-state cleanup, exactly like a DONE/FAILED job would.

    def _on_stop_checksum_error(self, exp_name, msg):
        self._checksum_stop_workers.pop(exp_name, None)
        buttons = self._row_buttons.get(exp_name)
        if buttons:
            buttons[1].setEnabled(True)
        self._log(f"Failed to stop '{exp_name}': {msg}")

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                self.config = json.load(f)
        else:
            self.config = {"settings": {}, "experiments": []}

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(QtWidgets.QLabel("Most recent experiments per beamline:"))
        header_layout.addStretch()

        add_experiment_btn = QtWidgets.QPushButton("Add EXPID...")
        add_experiment_btn.clicked.connect(self.add_experiment)
        header_layout.addWidget(add_experiment_btn)

        if self.show_font_control:
            header_layout.addWidget(QtWidgets.QLabel("Font size:"))
            self.font_size_spin = QtWidgets.QSpinBox()
            self.font_size_spin.setRange(6, 24)
            self.font_size_spin.setValue(self.font_size)
            self.font_size_spin.valueChanged.connect(self.set_font_size)
            header_layout.addWidget(self.font_size_spin)

        layout.addLayout(header_layout)

        self.table_widget = QtWidgets.QTableWidget()
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels([
            "Expid", "Upload Status", "Files", "Actions", "History"
        ])
        self.table_widget.horizontalHeader().setStretchLastSection(False)
        # This is a read-only status dashboard, not an editable grid -
        # clicking a cell (including just near one of the Scan/Verify/
        # History buttons) has no effect on anything, so Qt's default
        # "current cell" selection highlight + bolded row/column header is
        # pure visual noise here, not a real state. Turn it off outright
        # rather than fight the symptom cell by cell.
        self.table_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table_widget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.table_widget.horizontalHeader().setHighlightSections(False)
        self.table_widget.verticalHeader().setHighlightSections(False)
        # Column widths are sized to content once rows are populated (see
        # the resizeColumnsToContents() call in _discover_and_populate_
        # experiments) rather than hardcoded here, so they scale with font
        # size instead of clipping at anything other than whatever size
        # these pixel guesses were tuned for.

        layout.addWidget(self.table_widget)

        self.aggregate_label = QtWidgets.QLabel("")
        self.aggregate_label.setWordWrap(True)
        layout.addWidget(self.aggregate_label)

        # Word-wrapped: some error messages here embed a full remote
        # command line (see _on_checksum_launch_error/_on_upload_error) -
        # without wrapping, a QLabel's sizeHint grows to fit that text on
        # one line, which stretches the whole window wider every time one
        # of those fires instead of just growing the status bar's height.
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Scrollable history of every status/error message (see _log) -
        # the label above only ever shows the latest one, so a long SSH
        # failure got overwritten by the next poll tick before it could be
        # read in full, even after word-wrapping fixed the width problem.
        console_header = QtWidgets.QHBoxLayout()
        console_header.addWidget(QtWidgets.QLabel("Console:"))
        console_header.addStretch()
        clear_console_btn = QtWidgets.QPushButton("Clear")
        clear_console_btn.clicked.connect(lambda: self.console.clear())
        console_header.addWidget(clear_console_btn)
        layout.addLayout(console_header)

        self.console = QtWidgets.QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(2000)  # cap growth for a long-running session
        self.console.setFixedHeight(140)
        layout.addWidget(self.console)

        self.setLayout(layout)

    def _beamline_for_exp(self, exp_name):
        """Look up the Beamline column's value for exp_name's row, if the
        table is currently in the 6-column (auto-discovery) layout."""
        if self.table_widget.columnCount() < 6:
            return None
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 0)
            if item and item.text() == exp_name:
                beamline_item = self.table_widget.item(row, 1)
                return beamline_item.text() if beamline_item else None
        return None

    def _register_local_root(self, exp_name, local_root):
        """Record a known local_root for exp_name, in-memory only (never
        written back to the config file) - used when discovery finds the
        path directly (local s1c/s20a scan) so Scan/Verify/preview never
        need to guess a convention path or prompt for one."""
        for exp in self.config.get("experiments", []):
            if exp.get("name") == exp_name:
                exp["local_root"] = local_root
                return
        self.config.setdefault("experiments", []).append(
            {"name": exp_name, "local_root": local_root, "dataset": None})

    def _remote_info_for_beamline(self, beamline):
        """(remote_host, remote_user, setup_script) for beamline's DM
        queries - see dm_integrity.remote_info_for_beamline, shared with
        the CLI so both route the same way."""
        return di.remote_info_for_beamline(self.config, beamline)

    def _resolve_local_root(self, exp_name, beamline, try_convention=True, allow_prompt=True):
        """Find where exp_name's local data lives: an explicit config entry
        first, then - if try_convention - the per-beamline convention path
        (settings.local_root_templates), then - only if allow_prompt - a
        folder picker. Returns the path, or None if nothing was found/picked.

        The automatic, non-interactive preview during discovery
        (_update_experiment_row) calls this with both False: convention-path
        experiments are usually still actively being acquired (nothing
        cleaned up yet, real dirs), so trying the convention path there would
        turn every GUI startup into a real SSH round-trip per matching row -
        several seconds each, times up to 10 rows. Scan/Verify MD5, an
        explicit single-experiment click the user is already waiting on,
        gets the full resolution (try_convention=True, allow_prompt=True).
        """
        for exp in self.config.get("experiments", []):
            if exp.get("name") == exp_name and exp.get("local_root"):
                return exp["local_root"]

        if not try_convention:
            return None

        settings = self.config.get("settings", {})
        templates = settings.get("local_root_templates", {})
        template = templates.get(beamline) if beamline else None
        if template:
            # ~-relative (e.g. "~/mnt/s1c/{expid}") so this resolves
            # correctly regardless of which account launched the GUI -
            # canonicalize before checking/returning it.
            candidate = di.canonical_local_root(template.format(expid=exp_name))
            if os.path.isdir(candidate):
                return candidate

        if not allow_prompt:
            return None

        start_dir = os.path.dirname(di.canonical_local_root(template.format(expid=exp_name))) if template else ""
        chosen = _choose_directory(self, f"Select local data folder for '{exp_name}'", start_dir)
        return chosen or None

    def _paint_experiment_row(self, row, report):
        """Paint one row's Upload Status/Files cells and background color
        from an already-computed report. Pure UI update, no DM queries -
        callers that already have a report (e.g. _on_scan_finished, or
        _poll_checksum_jobs loading a completed checksum job's saved
        report) call this directly rather than re-running the whole
        SSH/scan pipeline synchronously just to redraw a row whose data is
        already sitting right there.
        """
        six_col = self.table_widget.columnCount() >= 6
        status_col, files_col = (2, 3) if six_col else (1, 2)

        file_stats = report["file_stats"]
        good_count = file_stats["good"]
        bad_count = file_stats["bad"]
        sojourner_status = report["sojourner_status"]
        upload_status = report["upload_status"]

        upload_status_item = QtWidgets.QTableWidgetItem(sojourner_status.replace("_", " ").title())
        upload_status_item.setToolTip(report["sojourner_summary"])
        self.table_widget.setItem(row, status_col, upload_status_item)

        files_text = f"{good_count} good / {bad_count} bad"
        files_item = QtWidgets.QTableWidgetItem(files_text)

        # file_stats["remote_only"]/["size_mismatch"] are already the
        # post-relocation counts build_report() computes (see its own
        # docstring) - a relocated pair no longer trips has_problem here,
        # which is the direct fix for the miscalibration this feature was
        # built for: a fully-cleaned-up-after-upload experiment used to
        # paint every REMOTE_ONLY file red indistinguishably from actually
        # missing/lost data.
        has_problem = file_stats["size_mismatch"] > 0 or file_stats["remote_only"] > 0 or file_stats["checksum_mismatch"] > 0
        if sojourner_status == "FULLY_LANDED" and upload_status.get("upload_complete", False) and not has_problem:
            bg_color = STATUS_COLORS["good"]
        elif has_problem:
            # A real integrity problem (not just "hasn't uploaded yet") -
            # checked before "good" specifically so a checksum mismatch on
            # an otherwise size-matched (FULLY_LANDED) file can't be
            # outranked by the good-color check above.
            bg_color = STATUS_COLORS["problem"]
        elif sojourner_status == "NOT_ON_SOJOURNER":
            # The expected state for a currently-running experiment -
            # worth a glance, not a red flag.
            bg_color = STATUS_COLORS["attention"]
        elif bad_count > 0:
            bg_color = STATUS_COLORS["noncritical"]
        else:
            bg_color = QtGui.QColor(255, 255, 255)

        files_item.setBackground(bg_color)
        self.table_widget.setItem(row, files_col, files_item)

        for col in range(files_col + 1):
            cell = self.table_widget.item(row, col)
            if cell:
                cell.setBackground(bg_color)

        self._recompute_aggregate_summary()

        # A fresh report here means save_record just wrote a new one for
        # this row - refresh its "N recs" indicator (see _history_summary)
        # so it reflects the new count/last-result immediately, not just
        # after the next full table rebuild.
        exp_item = self.table_widget.item(row, 0)
        if exp_item:
            exp_name = exp_item.text()
            self._refresh_history_summary(exp_name, self._beamline_for_exp(exp_name))

    def _recompute_aggregate_summary(self):
        """Per-beamline rollup line ('s1: 2/3 scanned - 1 on Sojourner, 0
        not, 1 mismatch') over exactly the rows currently displayed - not a
        new DM/SSH sweep, purely a tally of whatever's already in
        self.last_reports from a Scan or completed Verify MD5. A row that
        hasn't been Scanned/Verified this session simply doesn't count yet
        (shown via the "N/M scanned" prefix) rather than triggering a query
        just to fill in the aggregate.

        "Mismatch" reuses _paint_experiment_row's own has_problem test (a
        real integrity issue - size mismatch, remote-only files, or a
        failed checksum) so the aggregate agrees with each row's own red/
        non-red coloring by construction, rather than recomputing a
        second, possibly-diverging notion of "mismatch".
        """
        if self.table_widget.columnCount() < 6:
            self.aggregate_label.setText("")
            return

        per_beamline = {}
        for row in range(self.table_widget.rowCount()):
            exp_item = self.table_widget.item(row, 0)
            beamline_item = self.table_widget.item(row, 1)
            if not exp_item or not beamline_item:
                continue
            beamline = beamline_item.text()
            counts = per_beamline.setdefault(
                beamline, {"total": 0, "scanned": 0, "on_sojourner": 0, "not_on_sojourner": 0, "mismatch": 0})
            counts["total"] += 1

            report = self.last_reports.get(exp_item.text())
            if not report:
                continue
            counts["scanned"] += 1

            file_stats = report["file_stats"]
            sojourner_status = report["sojourner_status"]
            has_problem = (file_stats["size_mismatch"] > 0 or file_stats["remote_only"] > 0
                           or file_stats["checksum_mismatch"] > 0)
            if has_problem:
                counts["mismatch"] += 1
            elif sojourner_status in ("NOT_ON_SOJOURNER", "NO_LOCAL_FILES"):
                counts["not_on_sojourner"] += 1
            else:
                counts["on_sojourner"] += 1

        lines = []
        for beamline in sorted(per_beamline):
            c = per_beamline[beamline]
            lines.append(
                f"{beamline}: {c['scanned']}/{c['total']} scanned - "
                f"{c['on_sojourner']} on Sojourner, {c['not_on_sojourner']} not, {c['mismatch']} mismatch"
            )
        self.aggregate_label.setText("  |  ".join(lines))

    def _on_scan(self, exp_name):
        self._run_scan(exp_name)

    def _set_scan_button_enabled(self, exp_name, enabled):
        buttons = self._row_buttons.get(exp_name)
        if buttons:
            buttons[0].setEnabled(enabled)

    def _run_scan(self, exp_name):
        if di is None:
            self._log("ERROR: dm module not available")
            return

        if exp_name in self._active_workers:
            self._log(f"Scan already running for '{exp_name}'")
            return

        # Resolving local_root can pop a folder picker (QFileDialog), which
        # must happen on the GUI thread - do this before handing off to the
        # background worker, not inside it.
        beamline = self._beamline_for_exp(exp_name)
        local_root = self._resolve_local_root(exp_name, beamline, try_convention=True, allow_prompt=True)
        if not local_root:
            self._log(f"Scan cancelled: no local folder selected for '{exp_name}'")
            return

        exp_config = None
        for exp in self.config.get("experiments", []):
            if exp.get("name") == exp_name:
                exp_config = exp
                break
        dataset = exp_config.get("dataset") if exp_config else None

        settings = self.config.get("settings", {})
        station_name = settings.get("station_name", "SOJOURNER")
        remote_host, remote_user, setup_script = self._remote_info_for_beamline(beamline)
        # Where Scan's own result gets *saved* - the beamline's shared
        # dm_record/, not wherever this GUI happens to be running, so
        # results are visible regardless of which account launched it.
        save_host, save_user, remote_base = di.remote_identity_for_beamline(self.config, beamline)
        legacy_records_dir = settings.get("records_dir", di.DEFAULT_RECORDS_DIR)

        self._log(f"Running lightweight scan for '{exp_name}' (running in background)...")
        self._set_scan_button_enabled(exp_name, False)

        thread = QtCore.QThread(self)
        worker = _ScanWorker(exp_name, station_name, remote_host, remote_user, setup_script,
                              local_root, dataset, save_host, save_user, remote_base, legacy_records_dir)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda report: self._on_scan_finished(exp_name, report))
        worker.error.connect(lambda msg: self._on_scan_error(exp_name, msg))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        # Keep references alive - nothing else holds them, and a GC'd thread
        # object mid-run silently kills the worker.
        self._active_workers[exp_name] = (thread, worker)
        thread.start()

    def _on_scan_finished(self, exp_name, report):
        self._active_workers.pop(exp_name, None)
        self._set_scan_button_enabled(exp_name, True)
        self.last_reports[exp_name] = report

        file_stats = report["file_stats"]
        msg = f"Scan complete: {report['sojourner_summary']} ({file_stats['good']} good / {file_stats['bad']} bad)"
        if report["recommend_deletion"]:
            msg += " - SAFE TO DELETE"
        self._log(msg)

        row = self._row_for_exp(exp_name)
        if row is not None:
            self._paint_experiment_row(row, report)

    def _on_scan_error(self, exp_name, msg):
        self._active_workers.pop(exp_name, None)
        self._set_scan_button_enabled(exp_name, True)
        self._log(f"Scan failed: {msg}")

    def _on_verify_md5(self, exp_name):
        self._launch_checksum_job(exp_name)

    def _launch_checksum_job(self, exp_name):
        """Kick off a detached Verify MD5 job on zion. This method only
        does the (backgrounded) launch - once systemd-run confirms the job
        started, this GUI's job is done; _poll_checksum_jobs picks up
        progress/completion purely from the shared status file from then
        on, with no ongoing connection to this launch."""
        if di is None:
            self._log("ERROR: dm module not available")
            return

        if exp_name in self._tracked_checksum_jobs or exp_name in self._checksum_launch_workers:
            self._log(f"Verification already running for '{exp_name}'")
            return

        beamline = self._beamline_for_exp(exp_name)
        local_root = self._resolve_local_root(exp_name, beamline, try_convention=True, allow_prompt=True)
        if not local_root:
            self._log(f"Verification cancelled: no local folder selected for '{exp_name}'")
            return
        # Canonicalize before it ever leaves this process: the job runs as
        # s1iduser/s20iduser on zion, not whoever launched this GUI, so a
        # ~-relative or home-prefixed path chosen here would be wrong there.
        local_root = di.canonical_local_root(local_root)

        checksum_host, checksum_user, remote_base = di.remote_identity_for_beamline(self.config, beamline)
        if not checksum_host or not remote_base:
            self._log(f"No checksum_hosts entry configured for beamline '{beamline}'")
            return

        exp_config = None
        for exp in self.config.get("experiments", []):
            if exp.get("name") == exp_name:
                exp_config = exp
                break
        dataset = exp_config.get("dataset") if exp_config else None

        settings = self.config.get("settings", {})
        station_name = settings.get("station_name", "SOJOURNER")
        dm_remote_host, dm_remote_user, dm_setup_script = self._remote_info_for_beamline(beamline)
        cpu_budget = settings.get("checksum_cpu_budget", 0.20)
        all_status_dirs = self._all_checksum_status_dirs()

        self._log(f"Launching checksum verification for '{exp_name}' (running in background)...")
        self._set_verify_button_enabled(exp_name, False)

        thread = QtCore.QThread(self)
        worker = _ChecksumLaunchWorker(
            exp_name, beamline, station_name, dm_remote_host, dm_remote_user, dm_setup_script,
            local_root, dataset, checksum_host, checksum_user, remote_base, cpu_budget, all_status_dirs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.launched.connect(lambda status: self._on_checksum_launched(exp_name, status))
        worker.error.connect(lambda msg: self._on_checksum_launch_error(exp_name, msg))
        worker.launched.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._checksum_launch_workers[exp_name] = (thread, worker)
        thread.start()

    def _on_checksum_launched(self, exp_name, status):
        self._checksum_launch_workers.pop(exp_name, None)
        self._tracked_checksum_jobs[exp_name] = status
        self._set_checksum_running_ui(exp_name, True)
        self._log(f"Checksum verification for '{exp_name}' launched on zion (running in background, survives closing this GUI)")
        row = self._row_for_exp(exp_name)
        if row is not None:
            self._paint_checksum_progress(row, status)

    def _on_checksum_launch_error(self, exp_name, msg):
        self._checksum_launch_workers.pop(exp_name, None)
        self._set_checksum_running_ui(exp_name, False)
        self._log(f"Failed to launch checksum verification for '{exp_name}': {msg}")

    def _on_history(self, exp_name):
        if di is None:
            _message_box(QtWidgets.QMessageBox.Critical, self, "Error", "dm module not available")
            return

        # Check both the current per-beamline shared location (where new
        # Scan/Verify MD5 records land, regardless of who launched the GUI)
        # and the legacy flat settings.records_dir (parkjs's own, from
        # before records moved per-beamline) so history saved either way
        # stays visible.
        beamline = self._beamline_for_exp(exp_name)
        settings = self.config.get("settings", {})
        records_dirs = []
        if beamline:
            _, _, remote_base = di.remote_identity_for_beamline(self.config, beamline)
            if remote_base:
                records_dirs.append(di.checksum_records_dir(remote_base))
        legacy_records_dir = settings.get("records_dir", di.DEFAULT_RECORDS_DIR)
        if legacy_records_dir not in records_dirs:
            records_dirs.append(legacy_records_dir)

        records = []
        for records_dir in records_dirs:
            records.extend(di.list_records(records_dir, exp_name))
        records.sort(key=lambda r: r[0])

        if not records:
            _message_box(QtWidgets.QMessageBox.Information, self, "History", f"No records found for '{exp_name}'")
            return

        # Same "dserv" convention upload_info_for_experiment uses (the
        # basename of settings.local_bases[beamline], e.g. "s1c"/"s20a") -
        # just for labeling the local-only/relocated categories in the
        # dialog, not for any path computation.
        local_base = settings.get("local_bases", {}).get(beamline)
        local_label = os.path.basename(local_base.rstrip("/")) if local_base else "local"

        # Logged unconditionally before attempting to open, and the whole
        # attempt wrapped in try/except reporting through self._log (the
        # main window's own status label/console - already confirmed
        # rendering correctly, unlike a brand-new dialog on this flaky
        # display) rather than a fresh _message_box: confirmed directly
        # that History could silently do nothing - no new window, no
        # taskbar entry, and no terminal output either - with no way to
        # tell whether the click was even received, a dialog construction
        # exception happened, or the dialog was created but never mapped
        # by the X server. This makes each of those cases distinguishable
        # instead of all looking identical from the user's side.
        self._log(f"Opening History for '{exp_name}'...")
        try:
            dialog = HistoryDetailDialog(self, exp_name, records, local_label)
            _center_on_parent(dialog, self)
            dialog.exec_()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._log(f"Failed to open History for '{exp_name}': {e}")

    def _log(self, msg):
        """Update the one-line status label AND append a timestamped entry
        to the scrollable console below it. The label alone can only ever
        show the latest message - a long SSH failure (a full remote
        command line, or DM's own stderr) got overwritten by the next poll
        tick before it could be read in full, even after word-wrapping
        fixed the label's width problem. Every self.status_label.setText
        call site in this class goes through here instead."""
        self.status_label.setText(msg)
        line = "[{}] {}".format(time.strftime("%H:%M:%S"), msg)
        cursor = self.console.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        if any(kw in msg.lower() for kw in ("failed", "error", "can't", "cancelled")):
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor("#c0392b"))
            cursor.insertText(line + "\n", fmt)
        else:
            cursor.insertText(line + "\n")
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()

    def set_font_size(self, size):
        self.font_size = size
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self.table_widget.setFont(font)
        self.table_widget.horizontalHeader().setFont(font)
        self.console.setFont(font)
        if self.show_font_control:
            self.font_size_spin.setFont(font)
        # Column widths are content-driven (see _init_ui/_discover_and_
        # populate_experiments), not hardcoded pixels, specifically so they
        # scale with font size instead of clipping header text/buttons at
        # larger sizes - resize both dimensions now that the font changed.
        self.table_widget.resizeColumnsToContents()
        self.table_widget.resizeRowsToContents()


class DataIntegrityWindow(QtWidgets.QMainWindow):
    def __init__(self, config_path):
        super().__init__()
        self.setWindowTitle("Data Integrity")
        self.resize(800, 400)

        self.panel = DataIntegrityPanel(config_path, show_font_control=True)
        self.setCentralWidget(self.panel)

        toolbar = self.addToolBar("View")
        toolbar.addWidget(QtWidgets.QLabel(" Font size: "))
        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(6, 24)
        self.font_size_spin.setValue(10)
        self.font_size_spin.valueChanged.connect(self.set_font_size)
        toolbar.addWidget(self.font_size_spin)

        self.set_font_size(10)

    def set_font_size(self, size):
        self.panel.set_font_size(size)


def main(config_path=None):
    if config_path is None:
        config_path = os.path.join(SCRIPT_DIR, "data_integrity_config.json")

    app = QtWidgets.QApplication(sys.argv[:1])
    window = DataIntegrityWindow(config_path)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
