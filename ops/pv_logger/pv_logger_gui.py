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
import json
import os
import shlex
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

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
    # resize()d itself - it otherwise still reports a placeholder width/
    # height at this point. WA_Resized is set automatically by resize()
    # (Qt's own way of tracking "has this widget been given an explicit
    # size"), so this skips adjustSize() for a dialog that deliberately
    # resized itself larger than its layout's natural minimum.
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


def _choose_save_file(parent, title, start_dir="", filter_str=""):
    """Drop-in replacement for QtWidgets.QFileDialog.getSaveFileName's
    static convenience method, for the same reason _message_box replaces
    QMessageBox's (confirmed directly in data_integrity's dm_integrity_gui.py -
    a native/unpositioned file picker reproduced the identical no-error-
    nothing-visible symptom). DontUseNativeDialog matters here
    specifically: getSaveFileName defaults to the platform's own native
    picker when available, which is a separate windowing stack outside
    Qt's show()/raise_()/activateWindow() control - _center_on_parent
    can't do anything for a window it was never involved in creating."""
    dialog = QtWidgets.QFileDialog(parent, title, start_dir, filter_str)
    dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
    dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    _center_on_parent(dialog, parent)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        selected = dialog.selectedFiles()
        return selected[0] if selected else ""
    return ""


def _choose_open_file(parent, title, start_dir="", filter_str=""):
    """Drop-in replacement for QtWidgets.QFileDialog.getOpenFileName's
    static convenience method - same reasoning as _choose_save_file/
    _choose_directory (a native picker is a separate windowing stack
    _center_on_parent can't reach). Used for "Load selection from CSV...",
    picking an EXISTING file rather than naming a new one."""
    dialog = QtWidgets.QFileDialog(parent, title, start_dir, filter_str)
    dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    _center_on_parent(dialog, parent)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        selected = dialog.selectedFiles()
        return selected[0] if selected else ""
    return ""

# Device-type groupings for the Start-new-experiment checklist, so related
# groups (e.g. the 8 different furnace groups, scattered across the
# alphabet under names like "FZHANG COLD SINTER FURNACE"/"RF Furnace"/
# "SUTER-BASIL FURNACE") land together instead of a flat alphabetical list
# of ~80 groups. Presentation-only - doesn't touch the master list's own
# "group" field or PV filtering, which still key off the group name
# exactly as before. A group name not listed here (e.g. one a rename just
# created) falls into the "Other" catch-all category rather than being
# dropped, so this mapping can lag behind the master lists without
# breaking anything - just showing up uncategorized until updated.
DEVICE_CATEGORIES = [
    ("Detectors", [
        "GE/Pilatus DETECTOR", "Pilatus", "PIXIRAD2", "NF DET", "Tomo det",
        "Detectors (armed state)", "DETECTORS frame number", "BSE1 Detector", "BSE2 Detector",
        "D3 Detector", "D4-1 Detector", "D4-2 Detector", "GH2 Detector", "PG6 Detector",
        "PITEC1 Detector", "Varex Detector",
    ]),
    ("Optics / Lenses", [
        "LENSES", "LENSES IN B CRL, upstream", "LENSES IN B VERTICAL FOCUS",
        "LENSES IN E Horizontal FOCUS", "LENSES IN E VERTICAL FOCUS", "LENGELER LENSES IN B",
        "CRL LENSES IN DS C", "C-HUTCH LENSES", "E-HUTCH LENSES", "US CRL LENSES IN B",
    ]),
    ("Monochromators", ["HEM", "HEM (Monochromator)", "HRM", "HRM (Analyzer)", "Monochromator"]),
    ("Slits", ["Slits"]),
    ("Scalers / Ion Chambers", [
        "C Scaler (raw channels)", "E Scaler (raw channels)",
        "IC from scaler1 in 1id", "IC from scaler1 in 1ide", "Ion Chamber",
    ]),
    ("Furnaces / Heating", [
        "CMU Suter / Basil furnace motors", "FZHANG COLD SINTER FURNACE",
        "HASTINGS FURNACE", "IR FURNACE", "LANL RF FURNACE", "LINKAM FURNACE", "RF Furnace",
        "SUTER-BASIL FURNACE",
    ]),
    ("Load Frames / Mechanical Testing", [
        "Compact loadframe", "Compact loadframe UL / DESY", "meimei psylotech load frame",
        "MTS", "MTS - BIAXIAL", "MTS+RAMS1+OXYGON setup", "RAMS1", "RAMS3", "OWIS compression type",
    ]),
    ("Sample Stages / Motors", [
        "Aero setup", "AM chamber setup", "C 4-Circle Stage", "E HL-SMS",
        "MAMC setup", "NIST BOULDER CONNOLLY H2 CHAMBER", "Motors",
    ]),
    ("Sensors / Environmental", [
        "KEYENCE", "TILT SENSORS", "FLOW METER", "Hutch monitoring thermocouples", "THERMOCOUPLE",
    ]),
    ("Beam / Storage Ring", ["Beam positions", "Storage Ring Status", "Experiment Identifiers", "Scan Parameters"]),
    ("Lab Equipment", ["LANL CHILLER", "LANL WELDER", "AGILENT FUNC GEN"]),
    ("Shutters / Shields / Foils", ["Shields", "Shutters", "Foils. attens"]),
    ("Software / Misc", [
        "INITATE LOGGING", "handshake signals", "VOLTAGE SIGNAL POKHAREL_MAR18",
        "write_parfile_general.mac (misc, review before use)", "Calculation/Software", "Miscellaneous",
    ]),
]

_CATEGORY_FOR_GROUP = {
    group: category for category, groups in DEVICE_CATEGORIES for group in groups
}

_OTHER_CATEGORY = "Other"


def _category_for_device(device):
    return _CATEGORY_FOR_GROUP.get(device, _OTHER_CATEGORY)


class StartExperimentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, default_dir="", devices=None, pv_defs=None, config_path=None):
        """pv_defs/config_path: the live master-list pv entries and the
        file they came from, so a rename here can actually rewrite the
        shared 'group' field on every matching PV entry and persist it -
        renaming a device is a permanent, shared edit to the master list
        (pv_master_list_s1.json/s20.json), not just a label change in this
        dialog. Both are optional (rename is simply unavailable without
        them) so this class stays usable in isolation/tests.
        """
        super().__init__(parent)
        self.setWindowTitle("Start new experiment")
        self._pv_defs = pv_defs
        self._config_path = config_path

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
        self._device_scroll = None
        self.device_group = None
        if devices:
            self.device_group = QtWidgets.QGroupBox("Select devices to monitor:")
            self.device_group.setLayout(QtWidgets.QVBoxLayout())

            filter_row = QtWidgets.QHBoxLayout()
            self.device_filter_edit = QtWidgets.QLineEdit()
            self.device_filter_edit.setPlaceholderText("Filter devices...")
            self.device_filter_edit.textChanged.connect(self._apply_device_filter)
            check_all_btn = QtWidgets.QPushButton("Check All")
            check_all_btn.clicked.connect(lambda: self._set_visible_devices_checked(True))
            uncheck_all_btn = QtWidgets.QPushButton("Uncheck All")
            uncheck_all_btn.clicked.connect(lambda: self._set_visible_devices_checked(False))
            filter_row.addWidget(self.device_filter_edit)
            filter_row.addWidget(check_all_btn)
            filter_row.addWidget(uncheck_all_btn)
            self.device_group.layout().addLayout(filter_row)

            checked = {device: True for device in devices}
            self._rebuild_device_checklist(devices, checked)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        if self.device_group is not None:
            layout.addWidget(self.device_group, 1)
        layout.addWidget(buttons)
        self.resize(500, 500)

    def _rebuild_device_checklist(self, devices, checked_state):
        """(Re)build the scrollable checkbox list from scratch - used both
        at construction and after a rename, so a rename's new sort
        position and any devices merged together by it are reflected
        correctly rather than patched in place. checked_state carries
        forward whatever was checked before the rebuild.

        Devices are grouped under DEVICE_CATEGORIES headers (in that
        list's order, "Other" last for anything unmapped), alphabetical
        within each category - related groups (e.g. every furnace) land
        together instead of a single flat alphabetical list of ~80 names.
        """
        if self._device_scroll is not None:
            self.device_group.layout().removeWidget(self._device_scroll)
            self._device_scroll.deleteLater()

        self.device_checks = {}
        self._category_headers = {}
        by_category = {}
        for device in devices:
            by_category.setdefault(_category_for_device(device), []).append(device)

        category_order = [c for c, _ in DEVICE_CATEGORIES if c in by_category]
        if _OTHER_CATEGORY in by_category:
            category_order.append(_OTHER_CATEGORY)

        device_layout = QtWidgets.QVBoxLayout()
        for category in category_order:
            header = QtWidgets.QLabel(category)
            bold_font = header.font()
            bold_font.setBold(True)
            header.setFont(bold_font)
            device_layout.addWidget(header)
            self._category_headers[category] = header

            # Case-insensitive, so mixed ALL-CAPS/Title Case/lowercase
            # device names (real examples here: "NF DET", "Pilatus",
            # "SUTER-BASIL FURNACE", "Shields") land in true alphabetical
            # order within the category rather than plain ASCII order,
            # where every uppercase letter sorts before every lowercase one.
            for device in sorted(by_category[category], key=str.lower):
                checkbox = QtWidgets.QCheckBox(device)
                checkbox.setChecked(checked_state.get(device, True))
                checkbox.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                checkbox.customContextMenuRequested.connect(
                    lambda pos, d=device: self._show_device_context_menu(d))
                self.device_checks[device] = checkbox
                device_layout.addWidget(checkbox)

        device_widget = QtWidgets.QWidget()
        device_widget.setLayout(device_layout)
        self._device_scroll = QtWidgets.QScrollArea()
        self._device_scroll.setWidgetResizable(True)
        self._device_scroll.setWidget(device_widget)
        # Deliberately no setMaximumHeight() here - the checklist is given
        # the outer layout's whole stretch (see layout.addWidget in
        # __init__), so resizing the dialog taller actually shows more
        # devices instead of leaving blank space above a capped-height
        # scroll area (confirmed directly: a 150px cap left most of a tall
        # dialog empty above just 4 visible rows).
        self.device_group.layout().addWidget(self._device_scroll)

        # Map device -> category once, reused by _apply_device_filter to
        # know which header to hide/show without recomputing it every
        # keystroke.
        self._device_category = {device: _category_for_device(device) for device in devices}

        if hasattr(self, "device_filter_edit"):
            self._apply_device_filter(self.device_filter_edit.text())

    def _show_device_context_menu(self, device):
        checkbox = self.device_checks.get(device)
        if checkbox is None:
            return
        menu = QtWidgets.QMenu(self)
        rename_action = menu.addAction("Rename...")
        if rename_action == menu.exec_(QtGui.QCursor.pos()):
            self._rename_device(device)

    def _rename_device(self, old_name):
        """Rename a device group, persisting to the master list file this
        dialog's devices came from (self._pv_defs/_config_path) - renames
        the shared 'group' field on every PV entry using old_name, so this
        affects every future run and anyone else using this tool, not just
        this dialog. Unavailable (silently) if the dialog wasn't given
        pv_defs/config_path - e.g. in isolation/tests.
        """
        if self._pv_defs is None or not self._config_path:
            return

        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Device", "New name:", text=old_name)
        new_name = new_name.strip()
        if not ok or not new_name or new_name == old_name:
            return

        if new_name in self.device_checks:
            reply = _message_box(
                QtWidgets.QMessageBox.Question, self, "Merge devices?",
                f"A device named '{new_name}' already exists. Rename "
                f"'{old_name}' into it? This merges all of '{old_name}'s "
                f"PVs under '{new_name}' in the master list.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if reply != QtWidgets.QMessageBox.Yes:
                return

        renamed_entries = [entry for entry in self._pv_defs if entry.get("group") == old_name]
        for entry in renamed_entries:
            entry["group"] = new_name

        try:
            # Re-read the file directly (not pl.load_config, which merges
            # in _DEFAULT_SETTINGS) so a save here only ever touches "pvs" -
            # settings already on disk, and anything else in the file,
            # come back out exactly as they went in.
            with open(self._config_path) as f:
                on_disk = json.load(f)
            on_disk["pvs"] = self._pv_defs
            pl.save_config(on_disk, self._config_path)
        except (OSError, ValueError) as e:
            for entry in renamed_entries:
                entry["group"] = old_name
            _message_box(
                QtWidgets.QMessageBox.Critical, self, "Rename failed", f"Could not save master list: {e}")
            return

        checked_state = {device: cb.isChecked() for device, cb in self.device_checks.items()}
        was_checked = checked_state.pop(old_name, True)
        checked_state[new_name] = checked_state.get(new_name, False) or was_checked
        self._rebuild_device_checklist(list(checked_state.keys()), checked_state)


    def _browse(self):
        path = _choose_save_file(self, "Output CSV", self._default_dir, "CSV files (*.csv)")
        if path:
            self.outfile_edit.setText(path)

    def _apply_device_filter(self, text):
        """Hide checkboxes whose device name doesn't contain text
        (case-insensitive substring). Paired with Check All/Uncheck All
        acting only on visible checkboxes (see _set_visible_devices_checked),
        this is how similarly-named devices (e.g. everything with "LENSES"
        in the name) get selected together: filter, then Check All.

        Also hides a category header once none of its devices match, so
        filtering doesn't leave a dangling "Furnaces / Heating" label
        sitting above zero visible checkboxes.
        """
        needle = text.strip().lower()
        visible_categories = set()
        for device, checkbox in self.device_checks.items():
            visible = not needle or needle in device.lower()
            checkbox.setVisible(visible)
            if visible:
                visible_categories.add(self._device_category.get(device))

        for category, header in self._category_headers.items():
            header.setVisible(category in visible_categories)

    def _set_visible_devices_checked(self, checked):
        for checkbox in self.device_checks.values():
            if checkbox.isVisible():
                checkbox.setChecked(checked)

    def outfile(self):
        return self.outfile_edit.text().strip()

    def selected_devices(self):
        """Return list of checked device names."""
        return [device for device, checkbox in self.device_checks.items()
                if checkbox.isChecked()]


class _PvLoggerLaunchWorker(QtCore.QObject):
    """Prepares and launches a detached PV-logging job on the beamline's
    remote_job host, off the GUI thread (the job spec write + launch is a
    handful of SSH round-trips). Mirrors dm_integrity_gui.py's
    _ChecksumLaunchWorker - this worker's own job ends the moment the
    launch succeeds; pv_logger.py's own `start` subcommand is the actual
    logging process from then on, detached and independent of this GUI.
    """

    launched = QtCore.pyqtSignal(dict)
    error = QtCore.pyqtSignal(str)

    def __init__(self, beamline, host, user, remote_base, outfile, filtered_cfg, selected_devices):
        super().__init__()
        self.beamline = beamline
        self.host = host
        self.user = user
        self.remote_base = remote_base
        self.outfile = outfile
        self.filtered_cfg = filtered_cfg
        self.selected_devices = selected_devices

    def run(self):
        # Same atomic-mkdir-lock guard rail as Scan/Verify MD5: the
        # status-file pre-check on the GUI thread is a fast common-case
        # filter, but it's check-then-act across different users'/sessions'
        # own GUI instances - this lock closes that race properly. Only
        # needs to cover the launch sequence itself, not the job's whole
        # runtime.
        lock_path = pl.lock_dir(self.remote_base, "pvlogger", self.beamline)
        if not pl.acquire_remote_lock(self.host, self.user, lock_path):
            self.error.emit(f"PV logging for '{self.beamline}' is already starting/running elsewhere.")
            return

        try:
            status_path = pl.pv_logger_status_path(self.remote_base, self.beamline)
            try:
                with open(status_path) as f:
                    existing = json.load(f)
                if existing.get("state") == "RUNNING":
                    self.error.emit(f"PV logging for '{self.beamline}' is already running (started by another user or session).")
                    return
            except (OSError, json.JSONDecodeError):
                pass

            job_spec_path = os.path.join(pl.pv_logger_status_dir(self.remote_base), f"{self.beamline}.jobspec")
            unit_name = pl.pv_logger_unit_name(self.beamline)
            worker_script_path = os.path.join(SCRIPT_DIR, "pv_logger.py")

            pl.write_remote_file(self.host, self.user, job_spec_path, json.dumps(self.filtered_cfg, indent=2))

            command = (
                "/usr/bin/python3 {script} start --config {spec} --outfile {outfile} --status-file {status}"
            ).format(
                script=shlex.quote(worker_script_path),
                spec=shlex.quote(job_spec_path),
                outfile=shlex.quote(self.outfile),
                status=shlex.quote(status_path),
            )
            pl.launch_detached_job(
                self.host, self.user, unit_name,
                description=f"PV logger: {self.beamline} ({', '.join(self.selected_devices[:3])}{'...' if len(self.selected_devices) > 3 else ''})",
                command=command,
                slice_name="pv-logger.slice",
            )

            self.launched.emit({"beamline": self.beamline, "outfile": self.outfile})
        except Exception as e:
            self.error.emit(str(e))
        finally:
            pl.release_remote_lock(self.host, self.user, lock_path)


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

        self.running = False
        self.current_beamline = "s1"
        self._launch_workers = {}  # beamline -> (QThread, _PvLoggerLaunchWorker), kept alive while launching

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

        # Polls the current beamline's remote status file - PV logging now
        # runs as a detached job on that beamline's remote_job host (see
        # start_experiment), so this GUI never touches EPICS or the CSV
        # file itself once a job is running; it only reads back what the
        # job already wrote. Always running (not just while self.running
        # is True) so it can pick up a job someone else started, or a
        # transition to STOPPED/FAILED, the same reattachment idea
        # data_integrity's checksum jobs use.
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._poll_pv_logger_status)
        poll_ms = int(self.cfg.get("settings", {}).get("log_interval_sec", 5) * 1000)
        self.timer.start(max(poll_ms, 1000))
        self._poll_pv_logger_status()

    def _on_beamline_changed(self, beamline_name):
        """Load config for selected beamline. Switching is always allowed,
        even mid-run - unlike the old in-process timer design, a running
        PV-logging job is now detached on its own remote host and keeps
        going regardless of what this GUI is currently looking at; the
        poll timer just starts watching a different beamline's status file
        and re-reattaches on switching back, the same as a fresh launch."""
        self.current_beamline = beamline_name

        config_file = os.path.join(self.base_config_dir, f"pv_master_list_{beamline_name}.json")

        if os.path.exists(config_file):
            try:
                self.cfg = pl.load_config(config_file)
                # This is the actual switch - every other method (start_
                # experiment's device list, saving recipients, etc.) reads
                # self.config_path, not a separate "current beamline" field,
                # so without this line they silently kept acting on
                # whichever file the panel happened to be constructed with,
                # regardless of this combo box (confirmed directly: s1 and
                # s20 showed the identical device checklist).
                self.config_path = config_file
                self.status_bar.showMessage(f"Switched to {beamline_name}")
            except Exception as e:
                self.status_bar.showMessage(f"Error loading {beamline_name} config: {str(e)}")
                self.cfg = pl.load_config(self.config_path)
        else:
            # Fallback to default config if beamline-specific one doesn't exist
            self.cfg = pl.load_config(self.config_path)
            self.status_bar.showMessage(f"Using default PV list for {beamline_name}")

        self._poll_pv_logger_status()

    def _paint_status(self, running):
        text = "RUNNING" if running else "STOPPED"
        color = STATUS_COLORS["running"] if running else STATUS_COLORS["stopped"]
        self.status_label.setText(text)
        palette = self.status_label.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(color))
        self.status_label.setPalette(palette)

    def _remote_job_info(self):
        """(host, user, remote_base) for the current beamline's persistent
        PV-logging job, from settings.remote_job - None, None, None if not
        configured (e.g. an older config file that predates this)."""
        remote_job = self.cfg.get("settings", {}).get("remote_job", {})
        return remote_job.get("host"), remote_job.get("user"), remote_job.get("remote_base")

    def start_experiment(self):
        host, user, remote_base = self._remote_job_info()
        if not remote_base:
            _message_box(
                QtWidgets.QMessageBox.Critical, self, "Not configured",
                f"No settings.remote_job configured for '{self.current_beamline}' - "
                "can't launch a PV-logging job.")
            return

        if self.running:
            _message_box(
                QtWidgets.QMessageBox.Warning, self, "Already running",
                f"PV logging is already running for '{self.current_beamline}'. Stop it first.")
            return

        # Load config and get all available devices
        self.cfg = pl.load_config(self.config_path)
        all_devices = pl.get_all_devices(self.cfg["pvs"])

        # Show dialog with device checklist
        dialog = StartExperimentDialog(
            self, devices=all_devices, pv_defs=self.cfg["pvs"], config_path=self.config_path)
        _center_on_parent(dialog, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        outfile = dialog.outfile()
        if not outfile:
            _message_box(QtWidgets.QMessageBox.Warning, self, "Missing output file", "Choose an output CSV path.")
            return

        selected_devices = dialog.selected_devices()
        if not selected_devices:
            _message_box(QtWidgets.QMessageBox.Warning, self, "No devices selected", "Select at least one device to monitor.")
            return

        # Canonicalize so a path chosen here (as whoever launched the GUI)
        # still resolves correctly once the job runs remotely as
        # user@host - the exact same reasoning data_integrity's Verify MD5
        # jobs use for local_root (see remote_job.canonical_path).
        outfile = pl.canonical_path(outfile)

        # Filter PVs to only those in selected devices, and package them
        # with a snapshot of settings as this job's config - written to
        # the remote host and passed as --config, so pv_logger.py's start
        # subcommand needs no new argument surface for device filtering.
        filtered_pvs = pl.filter_pvs_by_devices(self.cfg["pvs"], selected_devices)
        job_settings = dict(self.cfg["settings"])
        # Override the default state_file (a path under parkjs's own repo
        # checkout, not writable by s1iduser/s20iduser) with one under this
        # beamline's own remote_base - confirmed directly: without this,
        # the remote job crashes with a PermissionError the moment any
        # monitored PV goes offline and process_drop_alerts tries to
        # persist alert-cooldown state.
        job_settings["state_file"] = os.path.join(remote_base, "pv_alert_state.json")
        job_cfg = {"settings": job_settings, "pvs": filtered_pvs}

        beamline = self.current_beamline
        self.status_bar.showMessage(f"Launching PV logging for '{beamline}' on {host}...")

        thread = QtCore.QThread(self)
        worker = _PvLoggerLaunchWorker(beamline, host, user, remote_base, outfile, job_cfg, selected_devices)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.launched.connect(lambda status: self._on_pv_logger_launched(beamline, status))
        worker.error.connect(lambda msg: self._on_pv_logger_launch_error(beamline, msg))
        worker.launched.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._launch_workers[beamline] = (thread, worker)
        thread.start()


    def _on_pv_logger_launched(self, beamline, status):
        self._launch_workers.pop(beamline, None)
        self.status_bar.showMessage(
            f"PV logging for '{beamline}' launched on remote host (running in background, survives closing this GUI)")
        self._poll_pv_logger_status()

    def _on_pv_logger_launch_error(self, beamline, msg):
        self._launch_workers.pop(beamline, None)
        self.status_bar.showMessage(f"Failed to launch PV logging for '{beamline}': {msg}")
        _message_box(QtWidgets.QMessageBox.Critical, self, "Launch failed", msg)

    def stop_monitoring(self):
        host, user, remote_base = self._remote_job_info()
        if not remote_base:
            return
        unit_name = pl.pv_logger_unit_name(self.current_beamline)
        try:
            pl.run_shell_command(host, user, f"systemctl --user stop {unit_name}")
        except RuntimeError as e:
            _message_box(QtWidgets.QMessageBox.Critical, self, "Stop failed", str(e))
            return
        self.status_bar.showMessage(f"Stop requested for '{self.current_beamline}' - waiting for it to finish the current cycle...")
        self._poll_pv_logger_status()


    def _poll_pv_logger_status(self):
        """Re-read the current beamline's remote status file (plain local
        read - beamline service accounts' homes are on the same shared
        filesystem this GUI runs from, no SSH needed to read, only to
        write) and repaint. This is the entire reattachment mechanism too:
        a job started from a since-closed GUI, or a colleague's own GUI
        instance, shows up here exactly the same way as one this session
        launched itself.
        """
        host, user, remote_base = self._remote_job_info()
        if not remote_base:
            return

        status_path = pl.pv_logger_status_path(remote_base, self.current_beamline)
        try:
            with open(status_path) as f:
                status = json.load(f)
        except (OSError, json.JSONDecodeError):
            if self.running:
                self.running = False
                self._paint_status(running=False)
                self.stop_action.setEnabled(False)
            return

        state = status.get("state")
        if state == "RUNNING":
            self.running = True
            self._paint_status(running=True)
            self.stop_action.setEnabled(True)

            total = status.get("total_count", 0)
            online_count = status.get("online_count", 0)
            currently_offline = status.get("currently_offline", [])
            self.info_label.setText(
                "{} of {} PVs online  |  Output: {}".format(online_count, total, status.get("outfile", "?")))

            name_to_pv = {entry["name"]: entry["pv"] for entry in self.cfg.get("pvs", [])}
            self.offline_table.setRowCount(len(currently_offline))
            for row, name in enumerate(currently_offline):
                self.offline_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
                self.offline_table.setItem(row, 1, QtWidgets.QTableWidgetItem(name_to_pv.get(name, "")))

            updated_at = status.get("updated_at")
            if updated_at:
                self.status_bar.showMessage("Last write: {}".format(time.ctime(updated_at)))
        else:
            was_running = self.running
            self.running = False
            self._paint_status(running=False)
            self.stop_action.setEnabled(False)
            if was_running:
                if state == "FAILED":
                    self.status_bar.showMessage(
                        "PV logging failed for '{}': {}".format(
                            self.current_beamline, status.get("error_message", "unknown error")))
                elif state == "STOPPED":
                    finished_at = status.get("finished_at", time.time())
                    self.status_bar.showMessage(
                        "PV logging for '{}' stopped at {}".format(self.current_beamline, time.ctime(finished_at)))

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
