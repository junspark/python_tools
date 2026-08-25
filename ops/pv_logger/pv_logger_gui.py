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
import re
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

DEFAULT_FONT_SIZE = 10

STATUS_COLORS = {
    "running": "#c8f7c5",
    "stopped": "#e0e0e0",
    "failed": "#f7c5c5",
}

# Remembers the last PV selection used per beamline, keyed by PV "name"
# (not the raw PV string, and not device group - matches the granularity
# selected_pvs() now works at, and the same key read_logged_pv_names()
# pulls back out of a CSV's header row, so both the auto-remember and
# load-from-CSV paths feed the same representation). Deliberately its own
# small file rather than a key inside pv_master_list_s1/s20.json - this
# is ephemeral GUI convenience state, not part of the curated PV list
# those files hold.
_SELECTION_PREFS_PATH = os.path.join(SCRIPT_DIR, "pv_logger_selection_prefs.json")


def _load_selection_prefs():
    try:
        with open(_SELECTION_PREFS_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_selection_prefs(prefs):
    try:
        with open(_SELECTION_PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
    except OSError:
        pass  # best-effort - a stale/unwritable prefs file shouldn't block starting a logging run


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
        "Detectors (armed state)", "DETECTORS frame number", "Detector Acquisition Settings",
        "BSE1 Detector", "BSE2 Detector", "D3 Detector", "D4-1 Detector", "D4-2 Detector",
        "GH2 Detector", "PG6 Detector", "PITEC1 Detector", "Varex Detector",
    ]),
    ("Optics / Lenses", [
        "LENSES", "LENSES IN B CRL, upstream", "LENSES IN B VERTICAL FOCUS",
        "LENSES IN E Horizontal FOCUS", "LENSES IN E VERTICAL FOCUS", "LENGELER LENSES IN B",
        "CRL LENSES IN DS C", "C-HUTCH LENSES", "E-HUTCH LENSES", "US CRL LENSES IN B",
    ]),
    ("D Lens Stacks", [
        "D Lens Stack 1", "D Lens Stack 2", "D Lens Stack 3", "D Lens Stack 4",
        "D Lens Stack 5", "D Lens Stack 6",
    ]),
    ("E Lens Stacks", [
        "E Lens Stack 1", "E Lens Stack 2", "E Lens Stack 3", "E Lens Stack 4",
    ]),
    ("Monochromators", ["HEM", "HRM", "Monochromator"]),
    ("B Slits", ["B Slits"]),
    ("C Slits", ["C Upstream Slits", "C Downstream Slits"]),
    ("D Slits", ["D Upstream Slits", "D Downstream Slits", "D T7 Slits"]),
    ("E Slits", ["E Upstream Slits", "E Downstream Slits"]),
    ("White Beam Slits", ["White Beam Slits"]),
    ("Scalers / Ion Chambers", [
        "C Scaler (raw channels)", "E Scaler (raw channels)", "Ion Chamber",
        "A Hutch Ion Chambers", "B Hutch Ion Chambers", "C Hutch Ion Chambers",
        "D Hutch Ion Chambers", "E Hutch Ion Chambers",
    ]),
    ("Sample Environment", [
        "CMU Suter / Basil furnace motors", "FZHANG COLD SINTER FURNACE",
        "HASTINGS FURNACE", "IR FURNACE", "LANL RF FURNACE", "LINKAM FURNACE", "RF Furnace",
        "SUTER-BASIL FURNACE", "E PulseRay Furnace", "Linkam Furnace (old)",
        "NIST BOULDER CONNOLLY H2 CHAMBER", "LANL CHILLER", "LANL WELDER", "AM chamber setup",
    ]),
    ("Load Frames / Mechanical Testing", [
        "Compact loadframe", "Compact loadframe UL / DESY", "AML Psylotech muTS",
        "MTS", "MTS+RAMS1+OXYGON setup", "OWIS compression type",
    ]),
    ("Sample Stages / Motors", [
        "Motors",
    ]),
    ("Sample Manipulation Systems", [
        "C HR-SMS", "C 4-Circle Diffractometer", "D-HRSMS", "E HR-SMS", "E-HRSMS", "E-HLSMS", "E HL-SMS",
    ]),
    ("Sensors / Environmental", [
        "KEYENCE", "FLOW METER", "Hutch monitoring thermocouples", "THERMOCOUPLE", "TC32",
    ]),
    ("Beam / Storage Ring", [
        "Beam Position Monitor", "Storage Ring Status", "Experiment Identifiers", "Scan Parameters",
    ]),
    ("Storage Ring / Undulator", ["Storage Ring", "Undulator", "Insertion Devices"]),
    ("Lab Equipment", ["AGILENT FUNC GEN"]),
    ("Shutters / Shields / Foils", ["Shields", "Shutters", "Foils. attens", "Attenuator"]),
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


_T_NUMBER_RE = re.compile(r"[Tt](\d+)")
_CURRENT_NUMBER_RE = re.compile(r"Current(\d+)", re.IGNORECASE)


def _pv_sort_key(entry):
    """Order a device's per-PV checkboxes by hardware address (T-unit,
    then Current channel) rather than raw master-list/alphabetical order -
    confirmed directly that alphabetical-by-name scrambles a hutch's ion
    chambers relative to their actual T1/T2/T3 wiring (e.g. "IC7D" sorting
    next to "IC8D" alphabetically, while both actually being T3 Current1/
    Current2, next to unrelated T1/T2 entries in between). Falls back to
    plain alphabetical-by-name for anything that doesn't match this T<n>/
    Current<n> convention (most devices don't use it at all) - those
    entries carry no T/Current number to sort by, so they end up ordered
    only by name, exactly as before this existed.
    """
    pv = entry.get("pv", "")
    name = entry.get("name", "") or ""
    t_match = _T_NUMBER_RE.search(pv)
    current_match = _CURRENT_NUMBER_RE.search(pv)
    t_num = int(t_match.group(1)) if t_match else float("inf")
    current_num = int(current_match.group(1)) if current_match else float("inf")
    return (t_num, current_num, name.lower())


class _GroupCheckBox(QtWidgets.QCheckBox):
    """Tristate checkbox for a device group, whose PartiallyChecked state
    is only ever set programmatically (to indicate "some but not all of
    this device's PVs are individually selected") - never reachable by
    clicking it directly. Qt's own tristate checkboxes cycle through all
    three states on click by default, which would let a click land on
    "partially checked" with no sensible meaning as a deliberate user
    action here; overriding nextCheckState() (the standard, documented way
    to customize what a click does to a QCheckBox) keeps a click strictly
    a Checked/Unchecked toggle - "select all of this device's PVs" /
    "select none of them" - while still allowing the partial indicator to
    be shown as a passive reflection of the individual PV checkboxes
    underneath.
    """

    def nextCheckState(self):
        if self.checkState() == QtCore.Qt.Unchecked:
            self.setCheckState(QtCore.Qt.Checked)
        else:
            self.setCheckState(QtCore.Qt.Unchecked)


class StartExperimentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, default_dir="", devices=None, pv_defs=None, config_path=None,
                 initial_selected_pv_names=None):
        """pv_defs/config_path: the live master-list pv entries and the
        file they came from, so a rename here can actually rewrite the
        shared 'group' field on every matching PV entry and persist it -
        renaming a device is a permanent, shared edit to the master list
        (pv_master_list_s1.json/s20.json), not just a label change in this
        dialog. Both are optional (rename is simply unavailable without
        them) so this class stays usable in isolation/tests.

        initial_selected_pv_names: PV "name" values to start pre-checked
        (everything else starts unchecked) - the caller's own remembered-
        last-selection or loaded-from-CSV state. None (not just empty)
        means "no persisted selection to restore", falling back to the
        original default of everything checked - an empty set/list would
        instead mean "start with nothing checked", a real, different
        state (e.g. deliberately restoring an all-unchecked past run).
        """
        super().__init__(parent)
        self.setWindowTitle("Start new experiment")
        self._pv_defs = pv_defs
        self._config_path = config_path
        self._devices = devices or []
        # Guards the group<->per-PV checkbox sync (_on_group_checkbox_changed/
        # _on_pv_checkbox_changed) against re-entrant cascades: each side
        # sets this while it drives the other side's checkboxes, so that
        # drive doesn't itself trigger the first side's handler again.
        self._syncing_checks = False

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

            if pv_defs is not None:
                # Only meaningful with pv_defs in hand (need the master
                # list to match CSV column names back to actual PV
                # entries) - same "unavailable in isolation/tests"
                # pattern already used for rename.
                load_csv_row = QtWidgets.QHBoxLayout()
                load_csv_btn = QtWidgets.QPushButton("Load selection from CSV...")
                load_csv_btn.clicked.connect(self._load_selection_from_csv)
                load_csv_row.addWidget(load_csv_btn)
                load_csv_row.addStretch()
                self.device_group.layout().addLayout(load_csv_row)

            checked = {device: True for device in devices}
            pv_checked_state = None
            if initial_selected_pv_names is not None:
                selected_names = set(initial_selected_pv_names)
                pv_checked_state = {name: (name in selected_names)
                                     for entry in (pv_defs or []) for name in [entry.get("name")] if name}
            self._rebuild_device_checklist(devices, checked, pv_checked_state)

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

    def _rebuild_device_checklist(self, devices, checked_state, pv_checked_state=None):
        """(Re)build the scrollable checkbox list from scratch - used both
        at construction and after a rename, so a rename's new sort
        position and any devices merged together by it are reflected
        correctly rather than patched in place. checked_state carries
        forward whatever was checked before the rebuild.

        pv_checked_state: optional {pv_name: bool} for per-PV initial
        state (from __init__'s initial_selected_pv_names, or _rename_
        device's own capture of whatever was checked before the rename) -
        when given, a device with per-PV detail derives ITS group
        checkbox's initial tri-state from these values (so a partial
        restored selection shows correctly as PartiallyChecked right
        away) instead of every PV just following checked_state's whole-
        device value. None (the rebuild-callers' original default before
        this existed) means "no per-PV information available", falling
        back to every PV matching its device's checked_state entry.

        Devices are grouped under DEVICE_CATEGORIES headers (in that
        list's order, "Other" last for anything unmapped), alphabetical
        within each category - related groups (e.g. every furnace) land
        together instead of a single flat alphabetical list of ~80 names.
        """
        if self._device_scroll is not None:
            self.device_group.layout().removeWidget(self._device_scroll)
            self._device_scroll.deleteLater()

        # device -> [pv_entry, ...] (the actual {name, pv, group} dicts,
        # not just display strings - selected_pvs() needs the real entries
        # to build the job's PV list) for the expandable per-PV checkboxes
        # below. None (not just empty) when this dialog was built without
        # pv_defs (e.g. in isolation/tests, same case _rename_device is
        # already unavailable for), so the disclosure triangle and per-PV
        # checkboxes are skipped entirely rather than shown with nothing
        # real to check - that dialog falls back to whole-device
        # selection only, exactly like before this feature existed.
        pvs_by_device = None
        if self._pv_defs is not None:
            pvs_by_device = {}
            for entry in self._pv_defs:
                group = entry.get("group")
                if group:
                    pvs_by_device.setdefault(group, []).append(entry)

        self.device_checks = {}
        self._pv_checks = {}  # device -> [(pv_entry, checkbox), ...], only for devices with per-PV detail
        self._device_rows = {}  # device -> the row widget _apply_device_filter shows/hides as a unit
        self._device_toggles = {}  # device -> its disclosure QToolButton, so a PV-only filter match can auto-expand it
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
                device_pvs = pvs_by_device.get(device, []) if pvs_by_device is not None else []
                device_pvs = sorted(device_pvs, key=_pv_sort_key)

                checkbox = _GroupCheckBox(device) if device_pvs else QtWidgets.QCheckBox(device)
                checkbox.setChecked(checked_state.get(device, True))
                checkbox.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                checkbox.customContextMenuRequested.connect(
                    lambda pos, d=device: self._show_device_context_menu(d))
                self.device_checks[device] = checkbox

                row = QtWidgets.QWidget()
                row_layout = QtWidgets.QVBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(0)

                check_row = QtWidgets.QHBoxLayout()
                check_row.setContentsMargins(0, 0, 0, 0)
                if device_pvs:
                    # Expandable, not always-shown: showing every PV for
                    # every device inline (some groups - furnaces, motors -
                    # have dozens) would make the list far too long to
                    # scan; a disclosure triangle keeps it compact by
                    # default while still letting anyone check exactly
                    # which PVs a device name actually covers, on demand.
                    toggle = QtWidgets.QToolButton()
                    toggle.setArrowType(QtCore.Qt.RightArrow)
                    toggle.setCheckable(True)
                    toggle.setAutoRaise(True)
                    toggle.setFixedWidth(20)
                    check_row.addWidget(toggle)
                    self._device_toggles[device] = toggle
                else:
                    toggle = None
                    spacer = QtWidgets.QLabel()
                    spacer.setFixedWidth(20)
                    check_row.addWidget(spacer)
                check_row.addWidget(checkbox)
                check_row.addStretch()
                row_layout.addLayout(check_row)

                if device_pvs:
                    checkbox.setTristate(True)
                    group_checked = checked_state.get(device, True)

                    pv_row_widgets = []
                    detail = QtWidgets.QWidget()
                    detail_layout = QtWidgets.QVBoxLayout(detail)
                    detail_layout.setContentsMargins(28, 0, 0, 4)
                    detail_layout.setSpacing(2)
                    for entry in device_pvs:
                        label = f"{entry.get('name')}: {entry.get('pv')}" if entry.get("name") else entry.get("pv", "")
                        pv_checkbox = QtWidgets.QCheckBox(label)
                        pv_checkbox.setChecked(
                            pv_checked_state.get(entry.get("name"), group_checked)
                            if pv_checked_state is not None else group_checked)
                        pv_checkbox.stateChanged.connect(
                            lambda _state, d=device: self._on_pv_checkbox_changed(d))
                        detail_layout.addWidget(pv_checkbox)
                        pv_row_widgets.append((entry, pv_checkbox))
                    self._pv_checks[device] = pv_row_widgets

                    # Derive the group checkbox's own initial tri-state
                    # from the PVs just built, rather than trusting
                    # checked_state.get(device, True) blindly - a
                    # restored partial selection (some but not all of
                    # this device's PVs) needs to show as
                    # PartiallyChecked immediately, not as fully Checked/
                    # Unchecked until the user happens to touch one PV
                    # and trigger _on_pv_checkbox_changed's recompute.
                    if pv_checked_state is not None:
                        checked_count = sum(1 for _e, cb in pv_row_widgets if cb.isChecked())
                        if checked_count == 0:
                            checkbox.setCheckState(QtCore.Qt.Unchecked)
                        elif checked_count == len(pv_row_widgets):
                            checkbox.setCheckState(QtCore.Qt.Checked)
                        else:
                            checkbox.setCheckState(QtCore.Qt.PartiallyChecked)

                    detail.setVisible(False)
                    row_layout.addWidget(detail)
                    toggle.toggled.connect(
                        lambda checked, d=detail, t=toggle: (
                            d.setVisible(checked),
                            t.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)))

                    checkbox.stateChanged.connect(
                        lambda state, d=device: self._on_group_checkbox_changed(d, state))

                self._device_rows[device] = row
                device_layout.addWidget(row)

        # Without this, filtering down to just a few visible devices
        # visibly stretched each remaining row to fill the vertical space
        # freed up by all the hidden ones - confirmed directly (a filtered
        # BSE1/BSE2 pair went from a normal ~30px row height to ~556px
        # each). Each device is wrapped in a plain QWidget() "row"
        # container (for the checkbox + disclosure toggle + PV detail),
        # which defaults to a Preferred vertical size policy - happy to
        # grow into leftover layout space - unlike a bare QCheckBox
        # (Fixed by default), which is what every earlier, non-stretchy
        # version of this list used. A trailing stretch claims all that
        # leftover space itself instead, the standard QVBoxLayout fix.
        device_layout.addStretch()

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
        # Capture the CURRENT per-PV state across every device (not just
        # old_name) before rebuilding, so a rename doesn't reset anyone
        # else's partial selection back to all-or-nothing - PV names
        # don't change on a rename (only "group" does), so they carry
        # over into the rebuilt checklist unchanged by name.
        pv_checked_state = {
            entry.get("name"): cb.isChecked()
            for pv_list in self._pv_checks.values()
            for entry, cb in pv_list
        }
        self._rebuild_device_checklist(list(checked_state.keys()), checked_state, pv_checked_state)

    def _browse(self):
        path = _choose_save_file(self, "Output CSV", self._default_dir, "CSV files (*.csv)")
        if path:
            self.outfile_edit.setText(path)

    def _load_selection_from_csv(self):
        """Reconstruct a past run's exact PV selection from its logged
        CSV's header row (see pl.read_logged_pv_names) - lets anyone
        replicate ANY previous run's PV set on demand, not just whatever
        the dialog happened to remember from the single most recent
        session (see PVLoggerPanel.start_experiment's separate auto-
        remember-last-selection behavior). Replaces the current selection
        entirely (uncheck-then-check), rather than merging with whatever
        was already checked, so the result always matches that CSV
        exactly regardless of what state the dialog was in before this
        was clicked.
        """
        path = _choose_open_file(self, "Load selection from CSV", self._default_dir, "CSV files (*.csv)")
        if not path:
            return
        logged_names = set(pl.read_logged_pv_names(path))
        if not logged_names:
            _message_box(
                QtWidgets.QMessageBox.Warning, self, "Nothing to load",
                f"Could not find any logged PV names in '{path}' - is it a PV logger CSV file?")
            return

        matched = 0
        for pv_list in self._pv_checks.values():
            for entry, checkbox in pv_list:
                checkbox.setChecked(entry.get("name") in logged_names)
                if entry.get("name") in logged_names:
                    matched += 1
        unmatched = len(logged_names) - matched
        message = f"Restored {matched} PV(s) from '{os.path.basename(path)}'."
        if unmatched > 0:
            message += (f"\n\n{unmatched} name(s) from that CSV weren't found in the current master "
                        "list (renamed or removed since that run) and couldn't be restored.")
        _message_box(QtWidgets.QMessageBox.Information, self, "Selection loaded", message)

    def _apply_device_filter(self, text):
        """Hide device rows whose device name AND every one of its PVs'
        name/pv strings don't contain text (case-insensitive substring).
        Paired with Check All/Uncheck All acting only on visible checkboxes
        (see _set_visible_devices_checked), this is how similarly-named
        devices (e.g. everything with "LENSES" in the name) get selected
        together: filter, then Check All.

        Matching PV content, not just the device/group name, matters now
        that individual PVs are shown at all (see the per-PV checkboxes
        added under each device) - confirmed directly that searching e.g.
        "HDF1" found nothing under a device-name-only filter even though
        several real PVs contain it, since "HDF1" only ever appears inside
        specific PV names, never a device/group name itself. A device that
        only matches via a PV (not by its own name) is auto-expanded too,
        so the PV that actually matched isn't left hidden inside a
        collapsed row - otherwise the row appearing with nothing visibly
        matching in it would look like the filter did nothing.

        Also hides a category header once none of its devices match, so
        filtering doesn't leave a dangling "Furnaces / Heating" label
        sitting above zero visible checkboxes.
        """
        needle = text.strip().lower()
        visible_categories = set()
        for device in self.device_checks:
            name_matches = not needle or needle in device.lower()
            pv_matches = False
            if needle and not name_matches:
                for entry, _checkbox in self._pv_checks.get(device, []):
                    if needle in entry.get("pv", "").lower() or needle in entry.get("name", "").lower():
                        pv_matches = True
                        break
            visible = name_matches or pv_matches
            # Hides the whole row (checkbox + disclosure toggle + PV
            # detail as one unit), not just the checkbox - otherwise a
            # filtered-out device's toggle/expanded PV list would stay
            # visible with no checkbox next to it. checkbox.isVisible()
            # elsewhere (_set_visible_devices_checked) still reflects this
            # correctly on its own, since Qt's isVisible() accounts for
            # ancestor visibility automatically.
            self._device_rows[device].setVisible(visible)
            if pv_matches:
                toggle = self._device_toggles.get(device)
                if toggle is not None:
                    toggle.setChecked(True)
            if visible:
                visible_categories.add(self._device_category.get(device))

        for category, header in self._category_headers.items():
            header.setVisible(category in visible_categories)

    def _set_visible_devices_checked(self, checked):
        for checkbox in self.device_checks.values():
            if checkbox.isVisible():
                checkbox.setChecked(checked)

    def _on_group_checkbox_changed(self, device, state):
        """User (or Check All/Uncheck All - setChecked() fires the same
        stateChanged signal) toggled a device's group checkbox directly -
        cascade to every one of its per-PV checkboxes. Guarded by
        _syncing_checks so this doesn't re-fire when _on_pv_checkbox_changed
        is the one driving this checkbox's state (to show the partial
        indicator), and _GroupCheckBox.nextCheckState ensures `state` here
        is only ever Checked or Unchecked from a real click - Partially-
        Checked only ever arrives from _on_pv_checkbox_changed's own
        programmatic setCheckState call below, which is itself guarded."""
        if self._syncing_checks:
            return
        checked = state == QtCore.Qt.Checked
        self._syncing_checks = True
        try:
            for _entry, pv_checkbox in self._pv_checks.get(device, []):
                pv_checkbox.setChecked(checked)
        finally:
            self._syncing_checks = False

    def _on_pv_checkbox_changed(self, device):
        """One of device's per-PV checkboxes changed - recompute its group
        checkbox's state from how many of them are now checked (none -
        Unchecked, all - Checked, some - PartiallyChecked). Guarded by
        _syncing_checks for the same reason _on_group_checkbox_changed is."""
        if self._syncing_checks:
            return
        pv_checks = self._pv_checks.get(device, [])
        checked_count = sum(1 for _entry, cb in pv_checks if cb.isChecked())
        if checked_count == 0:
            new_state = QtCore.Qt.Unchecked
        elif checked_count == len(pv_checks):
            new_state = QtCore.Qt.Checked
        else:
            new_state = QtCore.Qt.PartiallyChecked
        self._syncing_checks = True
        try:
            self.device_checks[device].setCheckState(new_state)
        finally:
            self._syncing_checks = False

    def outfile(self):
        return self.outfile_edit.text().strip()

    def selected_devices(self):
        """Return list of device names with at least one selected PV
        (fully or partially checked) - QCheckBox.isChecked() is True for
        both Checked and PartiallyChecked, which is exactly "this device
        is involved at all", the only thing this is used for (the
        launched job's human-readable description, and the "did you
        select anything" guard). selected_pvs() is what actually
        determines which PVs get logged."""
        return [device for device, checkbox in self.device_checks.items()
                if checkbox.isChecked()]

    def selected_pvs(self):
        """Return the actual list of individually-selected PV entries
        (the {name, pv, group} dicts from the master list) - the real
        thing to log, now that selection can be finer-grained than whole
        device groups. A device with per-PV checkboxes contributes
        exactly its checked PVs (which may be a subset); a device without
        them (this dialog built without pv_defs, so there was never
        anything to individually check) falls back to "every PV in
        pv_defs belonging to a checked device", the original all-or-
        nothing behavior."""
        result = []
        for device, checkbox in self.device_checks.items():
            pv_checks = self._pv_checks.get(device)
            if pv_checks:
                result.extend(entry for entry, cb in pv_checks if cb.isChecked())
            elif checkbox.isChecked() and self._pv_defs:
                result.extend(entry for entry in self._pv_defs if entry.get("group") == device)
        return result


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
        # Diagnostic prints at each step (flush=True, since this runs off
        # the GUI thread and stdout may otherwise not appear promptly) -
        # confirmed directly that a launch can sit indefinitely on
        # "Launching..." with no error ever surfacing, and with plain SSH
        # connectivity to this exact host/user already verified working
        # and fast - narrowing down which specific step actually hangs
        # needs to see progress between them, not just before/after.
        print(f"[pv_logger launch] starting for beamline={self.beamline!r} host={self.host!r} user={self.user!r}", flush=True)

        # Same atomic-mkdir-lock guard rail as Scan/Verify MD5: the
        # status-file pre-check on the GUI thread is a fast common-case
        # filter, but it's check-then-act across different users'/sessions'
        # own GUI instances - this lock closes that race properly. Only
        # needs to cover the launch sequence itself, not the job's whole
        # runtime.
        lock_path = pl.lock_dir(self.remote_base, "pvlogger", self.beamline)
        print(f"[pv_logger launch] acquiring lock at {lock_path!r}...", flush=True)
        if not pl.acquire_remote_lock(self.host, self.user, lock_path):
            print("[pv_logger launch] lock already held - aborting", flush=True)
            self.error.emit(f"PV logging for '{self.beamline}' is already starting/running elsewhere.")
            return
        print("[pv_logger launch] lock acquired", flush=True)

        try:
            status_path = pl.pv_logger_status_path(self.remote_base, self.beamline)
            print(f"[pv_logger launch] checking local status file {status_path!r}...", flush=True)
            try:
                with open(status_path) as f:
                    existing = json.load(f)
                if existing.get("state") == "RUNNING":
                    print("[pv_logger launch] status file says already RUNNING - aborting", flush=True)
                    self.error.emit(f"PV logging for '{self.beamline}' is already running (started by another user or session).")
                    return
            except (OSError, json.JSONDecodeError):
                pass
            print("[pv_logger launch] status check done", flush=True)

            job_spec_path = os.path.join(pl.pv_logger_status_dir(self.remote_base), f"{self.beamline}.jobspec")
            unit_name = pl.pv_logger_unit_name(self.beamline)
            worker_script_path = os.path.join(SCRIPT_DIR, "pv_logger.py")

            job_spec_json = json.dumps(self.filtered_cfg, indent=2)
            print(f"[pv_logger launch] writing job spec ({len(job_spec_json)} bytes, "
                  f"{len(self.filtered_cfg.get('pvs', []))} PVs) to {job_spec_path!r}...", flush=True)
            pl.write_remote_file(self.host, self.user, job_spec_path, job_spec_json)
            print("[pv_logger launch] job spec written", flush=True)

            command = (
                "/usr/bin/python3 {script} start --config {spec} --outfile {outfile} --status-file {status}"
            ).format(
                script=shlex.quote(worker_script_path),
                spec=shlex.quote(job_spec_path),
                outfile=shlex.quote(self.outfile),
                status=shlex.quote(status_path),
            )
            print(f"[pv_logger launch] launching detached job (unit={unit_name!r})...", flush=True)
            pl.launch_detached_job(
                self.host, self.user, unit_name,
                description=f"PV logger: {self.beamline} ({', '.join(self.selected_devices[:3])}{'...' if len(self.selected_devices) > 3 else ''})",
                command=command,
                slice_name="pv-logger.slice",
            )
            print("[pv_logger launch] detached job launched successfully", flush=True)

            self.launched.emit({"beamline": self.beamline, "outfile": self.outfile})
            print("[pv_logger launch] launched signal emitted", flush=True)
        except Exception as e:
            print(f"[pv_logger launch] EXCEPTION: {e!r}", flush=True)
            self.error.emit(str(e))
        finally:
            print("[pv_logger launch] releasing lock...", flush=True)
            pl.release_remote_lock(self.host, self.user, lock_path)
            print("[pv_logger launch] lock released, run() returning", flush=True)


class PVLoggerPanel(QtWidgets.QWidget):
    """
    All PV-logger GUI behavior, as a plain QWidget rather than a
    QMainWindow, so it can be embedded as a tab in ops_gui.py as well as
    hosted standalone by PVLoggerWindow below.
    """

    #: every beamline this tool manages - the single source of truth for
    #: which rows _poll_all_beamlines shows, iterated in this fixed order.
    BEAMLINES = ["s1", "s20"]

    def __init__(self, config_path, parent=None, show_font_control=True):
        super().__init__(parent)
        self.config_path = config_path
        self.base_config_dir = os.path.dirname(config_path)
        self.cfg = pl.load_config(config_path)

        self.current_beamline = "s1"
        self._launch_workers = {}  # beamline -> (QThread, _PvLoggerLaunchWorker), kept alive while launching
        # beamline -> bool - unlike the old single self.running, both
        # beamlines can be running independent jobs at once (confirmed
        # directly: this tool always managed s1 and s20 as two entirely
        # separate detached jobs, but the display used to only ever show
        # whichever one was currently selected in the dropdown, with no
        # way to see both at a glance without switching back and forth).
        self._beamline_running = {beamline: False for beamline in self.BEAMLINES}
        # beamline -> (state, finished_at) last surfaced as a FAILED/
        # STOPPED popup - lets that transition be reported exactly once
        # per beamline even when it happens before this GUI ever observed
        # that beamline's job as RUNNING (see _update_beamline_row's own
        # comment for why gating on "was running before" isn't enough).
        self._last_shown_terminal_state = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QtWidgets.QToolBar()
        layout.addWidget(toolbar)

        # Beamline selector - still controls which beamline Start/Stop/
        # Edit recipients act on (those are inherently per-beamline
        # actions), but no longer which beamline's status is visible -
        # self.jobs_tree below always shows every beamline at once.
        toolbar.addWidget(QtWidgets.QLabel(" Beamline: "))
        self.beamline_combo = QtWidgets.QComboBox()
        self.beamline_combo.addItems(self.BEAMLINES)
        self.beamline_combo.currentTextChanged.connect(self._on_beamline_changed)
        toolbar.addWidget(self.beamline_combo)
        toolbar.addSeparator()

        # One top-level (color-coded RUNNING/STOPPED/FAILED) row per
        # beamline, always all visible at once - replaces the single
        # status banner that only ever showed whichever beamline happened
        # to be selected in the dropdown. Expandable per beamline into
        # every individually-tracked PV's own online/offline state, not
        # just the (usually much shorter) currently-offline subset.
        self.jobs_tree = QtWidgets.QTreeWidget()
        self.jobs_tree.setHeaderLabels(["Beamline / PV", "Status", "Details"])
        self.jobs_tree.header().setStretchLastSection(True)
        self.jobs_tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._beamline_tree_items = {}
        for beamline in self.BEAMLINES:
            item = QtWidgets.QTreeWidgetItem([beamline, "STOPPED", "No experiment started yet."])
            self.jobs_tree.addTopLevelItem(item)
            self._beamline_tree_items[beamline] = item
            self._paint_job_row(beamline, running=False)
        layout.addWidget(self.jobs_tree, 1)

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

        # Polls EVERY beamline's remote status file, not just whichever is
        # currently selected - PV logging now runs as a detached job on
        # each beamline's own remote_job host (see start_experiment), so
        # this GUI never touches EPICS or the CSV file itself once a job
        # is running; it only reads back what the job already wrote.
        # Always running (not just while a job this session launched is
        # active) so it can pick up a job someone else started, or a
        # transition to STOPPED/FAILED, the same reattachment idea
        # data_integrity's checksum jobs use.
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._poll_all_beamlines)
        poll_ms = int(self.cfg.get("settings", {}).get("log_interval_sec", 5) * 1000)
        self.timer.start(max(poll_ms, 1000))
        self._poll_all_beamlines()

    def _on_beamline_changed(self, beamline_name):
        """Load config for selected beamline - controls which beamline
        Start/Stop/Edit recipients act on. Switching is always allowed,
        even mid-run - a running PV-logging job is detached on its own
        remote host and keeps going regardless of what this GUI is
        currently looking at; self.jobs_tree already shows every
        beamline's status regardless of this selection, so switching
        doesn't affect what's displayed, only what the toolbar actions
        target."""
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

        self.stop_action.setEnabled(self._beamline_running.get(beamline_name, False))

    def _paint_job_row(self, beamline, running, failed=False):
        item = self._beamline_tree_items[beamline]
        if failed:
            text, color = "FAILED", STATUS_COLORS.get("failed", QtGui.QColor(255, 200, 200))
        else:
            text = "RUNNING" if running else "STOPPED"
            color = STATUS_COLORS["running"] if running else STATUS_COLORS["stopped"]
        item.setText(1, text)
        brush = QtGui.QBrush(QtGui.QColor(color))
        for col in range(3):
            item.setBackground(col, brush)

    def _remote_job_info(self, cfg=None):
        """(host, user, remote_base) for a beamline's persistent PV-logging
        job, from settings.remote_job - None, None, None if not configured
        (e.g. an older config file that predates this). Defaults to the
        currently-selected beamline's own self.cfg (what start_experiment/
        stop_monitoring act on); _poll_all_beamlines passes each other
        beamline's own freshly-loaded cfg explicitly instead."""
        cfg = self.cfg if cfg is None else cfg
        remote_job = cfg.get("settings", {}).get("remote_job", {})
        return remote_job.get("host"), remote_job.get("user"), remote_job.get("remote_base")

    def _cfg_for_beamline(self, beamline):
        """A beamline's own master PV list, independent of self.cfg/
        self.current_beamline (which only reflect whichever beamline is
        selected in the toolbar) - _poll_all_beamlines needs every
        beamline's own settings.remote_job and PV name->address mapping at
        once, regardless of dropdown selection. Reloaded from disk each
        call (small local JSON file, polled no more often than once per
        log_interval_sec) rather than cached, so edits to a master list
        made while the GUI is open still take effect without a relaunch."""
        if beamline == self.current_beamline:
            return self.cfg
        config_file = os.path.join(self.base_config_dir, f"pv_master_list_{beamline}.json")
        if not os.path.exists(config_file):
            return self.cfg
        try:
            return pl.load_config(config_file)
        except Exception:
            return self.cfg

    def _read_jobspec_names(self, remote_base, beamline):
        """The PV names actually requested for this beamline's most recent
        launch attempt - written (plain local file, see
        _PvLoggerLaunchWorker.run) before the remote job even starts, so
        it's available even when a run fails before ever getting to write
        its own "tracked" list into the status file (e.g. "No PVs online
        at discovery time"). Returns None if this beamline has never been
        launched (no jobspec file yet)."""
        jobspec_path = os.path.join(pl.pv_logger_status_dir(remote_base), f"{beamline}.jobspec")
        try:
            with open(jobspec_path) as f:
                spec = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        return [entry.get("name") for entry in spec.get("pvs", [])]

    def _set_job_children(self, beamline, online_names, offline_names, name_to_pv=None, neutral_names=()):
        """Rebuild a beamline row's expandable children, one per tracked
        PV. Offline PVs are listed first since they're the ones worth
        noticing at a glance, then confirmed-online ones, then any
        neutral/unknown ones (see _poll_all_beamlines: only a RUNNING
        job's per-cycle sample is trustworthy enough to assert a PV is
        actually online right now - a STOPPED/FAILED job's last-known
        currently_offline may be stale, or may not exist at all for a job
        that never got past discovery, so those show neutrally rather
        than being painted a false green)."""
        item = self._beamline_tree_items[beamline]
        was_expanded = item.isExpanded()
        item.takeChildren()
        name_to_pv = name_to_pv or {}
        offline_brush = QtGui.QBrush(QtGui.QColor(STATUS_COLORS["failed"]))
        online_brush = QtGui.QBrush(QtGui.QColor(STATUS_COLORS["running"]))
        neutral_brush = QtGui.QBrush(QtGui.QColor(STATUS_COLORS["stopped"]))
        for name in offline_names:
            child = QtWidgets.QTreeWidgetItem([name, "OFFLINE", name_to_pv.get(name, "")])
            for col in range(3):
                child.setBackground(col, offline_brush)
            item.addChild(child)
        for name in online_names:
            child = QtWidgets.QTreeWidgetItem([name, "online", name_to_pv.get(name, "")])
            for col in range(3):
                child.setBackground(col, online_brush)
            item.addChild(child)
        for name in neutral_names:
            child = QtWidgets.QTreeWidgetItem([name, "-", name_to_pv.get(name, "")])
            for col in range(3):
                child.setBackground(col, neutral_brush)
            item.addChild(child)
        item.setExpanded(was_expanded)

    def start_experiment(self):
        host, user, remote_base = self._remote_job_info()
        if not remote_base:
            _message_box(
                QtWidgets.QMessageBox.Critical, self, "Not configured",
                f"No settings.remote_job configured for '{self.current_beamline}' - "
                "can't launch a PV-logging job.")
            return

        if self._beamline_running.get(self.current_beamline):
            _message_box(
                QtWidgets.QMessageBox.Warning, self, "Already running",
                f"PV logging is already running for '{self.current_beamline}'. Stop it first.")
            return

        # Load config and get all available devices
        self.cfg = pl.load_config(self.config_path)
        all_devices = pl.get_all_devices(self.cfg["pvs"])

        # Show dialog with device checklist, pre-seeded from whatever
        # selection was used last time this beamline launched (see
        # _save_selection_prefs below) - None (not this beamline's key
        # missing from an otherwise-valid prefs file - see _load_selection_
        # prefs) means "never launched before here", falling back to
        # StartExperimentDialog's own everything-checked default.
        selection_prefs = _load_selection_prefs()
        initial_selected_pv_names = selection_prefs.get(self.current_beamline)
        dialog = StartExperimentDialog(
            self, devices=all_devices, pv_defs=self.cfg["pvs"], config_path=self.config_path,
            initial_selected_pv_names=initial_selected_pv_names)
        _center_on_parent(dialog, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        outfile = dialog.outfile()
        if not outfile:
            _message_box(QtWidgets.QMessageBox.Warning, self, "Missing output file", "Choose an output CSV path.")
            return

        selected_pvs = dialog.selected_pvs()
        if not selected_pvs:
            _message_box(QtWidgets.QMessageBox.Warning, self, "No devices selected", "Select at least one device/PV to monitor.")
            return
        # Only for the launched job's human-readable description below -
        # selected_pvs (not this, and not filter_pvs_by_devices) is what
        # actually determines which PVs get logged, now that selection
        # can be finer-grained than whole device groups (individual PV
        # checkboxes nested under each device).
        selected_devices = dialog.selected_devices()

        # Remember this exact selection for next time this beamline's
        # dialog opens - keyed by PV name (matches read_logged_pv_names'
        # own granularity), not device, so a partial in-device selection
        # is restored just as precisely as a whole-device one.
        selection_prefs[self.current_beamline] = [entry.get("name") for entry in selected_pvs]
        _save_selection_prefs(selection_prefs)

        # Canonicalize so a path chosen here (as whoever launched the GUI)
        # still resolves correctly once the job runs remotely as
        # user@host - the exact same reasoning data_integrity's Verify MD5
        # jobs use for local_root (see remote_job.canonical_path).
        outfile = pl.canonical_path(outfile)

        # The job's actual PV list, exactly as selected in the dialog -
        # packaged with a snapshot of settings as this job's config,
        # written to the remote host and passed as --config, so
        # pv_logger.py's start subcommand needs no new argument surface
        # for device/PV filtering.
        filtered_pvs = selected_pvs
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
        self._poll_all_beamlines()

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
        self._poll_all_beamlines()

    def _poll_all_beamlines(self):
        """Re-read EVERY beamline's remote status file (plain local read -
        beamline service accounts' homes are on the same shared filesystem
        this GUI runs from, no SSH needed to read, only to write) and
        repaint every row of self.jobs_tree, not just whichever beamline
        happens to be selected in the toolbar. This is the entire
        reattachment mechanism too: a job started from a since-closed GUI,
        or a colleague's own GUI instance, shows up here exactly the same
        way as one this session launched itself.
        """
        for beamline in self.BEAMLINES:
            cfg = self._cfg_for_beamline(beamline)
            host, user, remote_base = self._remote_job_info(cfg)
            name_to_pv = {entry["name"]: entry["pv"] for entry in cfg.get("pvs", [])}

            if not remote_base:
                self._beamline_running[beamline] = False
                self._paint_job_row(beamline, running=False)
                self._beamline_tree_items[beamline].setText(2, "Not configured.")
                self._set_job_children(beamline, [], [])
                if beamline == self.current_beamline:
                    self.stop_action.setEnabled(False)
                continue

            status_path = pl.pv_logger_status_path(remote_base, beamline)
            try:
                with open(status_path) as f:
                    status = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._beamline_running[beamline] = False
                self._paint_job_row(beamline, running=False)
                self._beamline_tree_items[beamline].setText(2, "No experiment started yet.")
                self._set_job_children(beamline, [], [])
                if beamline == self.current_beamline:
                    self.stop_action.setEnabled(False)
                continue

            state = status.get("state")
            # "tracked" is every PV this job was launched with (added to
            # the status payload specifically for this expandable list),
            # written on the job's first successful cycle. A job that
            # fails before ever getting that far (e.g. "No PVs online at
            # discovery time") never writes it, so fall back to the
            # jobspec file - written before the job even starts - for
            # what was actually requested, rather than this beamline's
            # entire master list (which would falsely imply every PV in
            # the whole device catalog was part of this run).
            tracked = status.get("tracked") or self._read_jobspec_names(remote_base, beamline) or []

            if state == "RUNNING":
                # Only a RUNNING job's own per-cycle sample is trustworthy
                # enough to assert a PV is actually online/offline right
                # now - see _set_job_children for the STOPPED/FAILED case.
                currently_offline = set(status.get("currently_offline", []))
                offline_names = [n for n in tracked if n in currently_offline]
                online_names = [n for n in tracked if n not in currently_offline]

                self._beamline_running[beamline] = True
                self._paint_job_row(beamline, running=True)
                total = status.get("total_count", len(tracked))
                online_count = status.get("online_count", len(online_names))
                self._beamline_tree_items[beamline].setText(
                    2, "{} of {} PVs online  |  Output: {}".format(
                        online_count, total, status.get("outfile", "?")))
                self._set_job_children(beamline, online_names, offline_names, name_to_pv)
                if beamline == self.current_beamline:
                    self.stop_action.setEnabled(True)
                    updated_at = status.get("updated_at")
                    if updated_at:
                        self.status_bar.showMessage("Last write: {}".format(time.ctime(updated_at)))
            else:
                self._beamline_running[beamline] = False
                failed = state == "FAILED"
                self._paint_job_row(beamline, running=False, failed=failed)
                if state == "FAILED":
                    detail = "Failed: {}".format(status.get("error_message", "unknown error"))
                elif state == "STOPPED":
                    finished_at = status.get("finished_at")
                    detail = "Stopped at {}".format(time.ctime(finished_at)) if finished_at else "Stopped."
                else:
                    detail = "No experiment started yet."
                self._beamline_tree_items[beamline].setText(2, detail)
                # Not RUNNING - the status file's own currently_offline (if
                # present at all) reflects whatever the last actual sample
                # cycle saw, which may be stale by now (or may not exist
                # at all for a job that never got past discovery), so show
                # what was requested neutrally rather than asserting a
                # possibly-false-green "online" for all of it.
                self._set_job_children(beamline, [], [], name_to_pv, neutral_names=tracked)
                if beamline == self.current_beamline:
                    self.stop_action.setEnabled(False)

                # Report a FAILED/STOPPED transition exactly once per
                # beamline, keyed by (state, finished_at) rather than
                # gated on "was this GUI's own in-memory flag previously
                # RUNNING" - confirmed directly that a job which fails
                # fast enough (e.g. "No PVs online at discovery time",
                # within the very first poll after launch) can jump
                # straight from never-observed-running to FAILED, and the
                # old was_running gate silently swallowed that failure's
                # reason entirely - indistinguishable from "nothing
                # happened at all", exactly the symptom reported. A
                # message box, not just a status bar line, for the same
                # reason every other real failure in this codebase gets
                # one: a transient status bar message is easy to miss.
                state_key = (state, status.get("finished_at"))
                if state in ("FAILED", "STOPPED") and state_key != self._last_shown_terminal_state.get(beamline):
                    self._last_shown_terminal_state[beamline] = state_key
                    if state == "FAILED":
                        msg = "PV logging failed for '{}': {}".format(
                            beamline, status.get("error_message", "unknown error"))
                        self.status_bar.showMessage(msg)
                        _message_box(QtWidgets.QMessageBox.Warning, self, "PV logging failed", msg)
                    elif state == "STOPPED":
                        finished_at = status.get("finished_at", time.time())
                        self.status_bar.showMessage(
                            "PV logging for '{}' stopped at {}".format(beamline, time.ctime(finished_at)))

    def set_font_size(self, size):
        font = QtWidgets.QApplication.instance().font()
        font.setPointSize(size)
        QtWidgets.QApplication.instance().setFont(font)
        self.jobs_tree.setFont(font)
        self.jobs_tree.header().setFont(font)
        for col in range(3):
            self.jobs_tree.resizeColumnToContents(col)
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
