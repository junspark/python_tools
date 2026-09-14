#!/usr/bin/env python3
"""
PV/AD Matcher GUI (PyQt5) - a front-end for correlate_ad_pvs.py.

Lets a user pick a pv_logger CSV, a group of area-detector HDF5 files, and
a set of PVs (by name and/or pv_master_list group), then run either the
per-frame or averaged correlation mode without touching the command line.
All the actual logic (timestamp resolution, interpolation, PV/group
resolution, CSV writing) lives in correlate_ad_pvs.py - this file only
wires it up to widgets and runs it off the GUI thread.

Usage
-----
  python correlate_ad_pvs_gui.py
  python correlate_ad_pvs_gui.py --config /path/to/pv_master_list.json
"""

import argparse
import contextlib
import os
import re
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import correlate_ad_pvs as cap
import pv_logger as pl
import pv_logger_gui as plg

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    sys.exit(
        "PyQt5 is required for the GUI but is not installed.\n"
        "Install it with:  pip install PyQt5\n"
        "(correlate_ad_pvs.py's own CLI works without it.)"
    )

DEFAULT_FONT_SIZE = plg.DEFAULT_FONT_SIZE


def _guess_beamline_from_path(path):
    """Best-effort beamline guess from a path segment like "s20a" or "s1b"
    - the mount-point naming convention under PARKJS/mnt/ (s1a, s1b, s1c,
    s20a). Returns "s1"/"s20", or None if no such segment is found.
    Used only to suggest a starting point for the "Beamline (for PV
    groups)" selector - a PV logger CSV and area-detector files living
    under an s20 mount almost certainly want s20's PV groups, and
    leaving the selector on whatever beamline it last happened to be
    (see the ActiveDMS mismatch this was added to fix) silently resolves
    groups against the wrong master list instead of erroring loudly."""
    if not path:
        return None
    for segment in re.split(r"[\\/]", path):
        m = re.fullmatch(r"s(1|20)[a-z]?", segment, re.IGNORECASE)
        if m:
            return "s" + m.group(1)
    return None


def _choose_open_files(parent, title, start_dir=""):
    """Multi-file equivalent of pv_logger_gui._choose_open_file - same
    DontUseNativeDialog/_center_on_parent fix (a native picker is a
    separate windowing stack _center_on_parent can't reach)."""
    dialog = QtWidgets.QFileDialog(parent, title, start_dir)
    dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    plg._center_on_parent(dialog, parent)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        return dialog.selectedFiles()
    return []


def _choose_directory(parent, title, start_dir=""):
    """Same DontUseNativeDialog/_center_on_parent fix as
    disk_monitor_gui.py's/dm_integrity_gui.py's own _choose_directory."""
    dialog = QtWidgets.QFileDialog(parent, title, start_dir)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    plg._center_on_parent(dialog, parent)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        selected = dialog.selectedFiles()
        return selected[0] if selected else ""
    return ""


def _show_text_dialog(parent, title, text):
    """Read-only scrollable text popup - used for `inspect`'s output,
    which can be longer than a QMessageBox comfortably shows."""
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QtWidgets.QVBoxLayout(dialog)
    body = QtWidgets.QPlainTextEdit()
    body.setReadOnly(True)
    body.setPlainText(text)
    layout.addWidget(body)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.resize(600, 400)
    plg._center_on_parent(dialog, parent)
    dialog.exec_()


class _StreamToSignal:
    """A write()/flush() file-like object that re-emits each complete
    line through a Qt signal - lets correlate_ad_pvs.py's plain print()
    warnings (e.g. the mtime/embedded-timestamp mismatch notice) surface
    in the GUI's log area instead of disappearing into this process's
    real stdout/stderr, without correlate_ad_pvs.py needing to know
    anything about Qt."""

    def __init__(self, emit_line):
        self._emit_line = emit_line
        self._buf = ""

    def write(self, text):
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line:
                self._emit_line(line)

    def flush(self):
        pass


class _CorrelateWorker(QtCore.QObject):
    """Runs one correlate_ad_pvs.py pass (per-frame or averaged) off the
    GUI thread - HDF5 reads and CSV interpolation over many files is
    real I/O + numpy work that would otherwise freeze the window."""

    progress = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, modes, pv_master_list_path, pv_names, groups, files, csv_path,
                 timestamp_attr, dataset_path, out_dir, out_path, max_gap_sec):
        super().__init__()
        self.modes = modes  # subset of ["per-frame", "averaged"], both allowed at once
        self.pv_master_list_path = pv_master_list_path
        self.pv_names = pv_names
        self.groups = groups
        self.files = files
        self.csv_path = csv_path
        self.timestamp_attr = timestamp_attr or None
        self.dataset_path = dataset_path or cap.DEFAULT_DATASET_PATH
        self.out_dir = out_dir or None
        self.out_path = out_path
        self.max_gap_sec = max_gap_sec

    def run(self):
        stream = _StreamToSignal(self.progress.emit)
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                pv_names = cap.resolve_pv_names(self.pv_master_list_path, self.pv_names, self.groups)
                pv_names, missing = cap.filter_available_pvs(self.csv_path, pv_names)
                if missing:
                    self.progress.emit(f"WARNING: {self.csv_path}: PV(s) not logged in this CSV, skipping: {', '.join(missing)}")
                if not pv_names:
                    raise ValueError(f"{self.csv_path}: none of the requested PVs are present in logged columns")

                # Each file's timestamps/interpolated PV values are read
                # once and reused for whichever output mode(s) were
                # checked, rather than re-reading the HDF5/CSV per mode.
                per_frame_count = 0
                averaged_rows = []
                for h5_path in self.files:
                    timestamps, source = cap.get_frame_timestamps(h5_path, self.timestamp_attr, self.dataset_path)
                    pv_values = cap.interpolate_pvs(self.csv_path, pv_names, timestamps, self.max_gap_sec)
                    summary = f"{h5_path}: {len(timestamps)} frame(s), timestamps from {source}"
                    if "per-frame" in self.modes:
                        out_file = cap.write_per_frame_csv(h5_path, pv_names, timestamps, pv_values, self.out_dir)
                        per_frame_count += 1
                        summary += f" -> {out_file}"
                    if "averaged" in self.modes:
                        averaged = {name: cap._average_value(name, values, values[0]) for name, values in pv_values.items()}
                        averaged_rows.append((os.path.basename(h5_path), float(np.mean(timestamps)), len(timestamps), averaged))
                    self.progress.emit(summary)

                messages = []
                if "per-frame" in self.modes:
                    messages.append(f"Wrote {per_frame_count} per-frame CSV(s).")
                if "averaged" in self.modes:
                    cap.write_averaged_csv(averaged_rows, pv_names, self.out_path)
                    messages.append(f"Wrote {len(averaged_rows)} row(s) -> {self.out_path}")
                self.finished.emit(" ".join(messages))
        except Exception as e:
            self.error.emit(str(e))


class CorrelateAdPvsPanel(QtWidgets.QWidget):
    """All PV/AD Matcher GUI behavior, as a plain QWidget so it can be
    embedded as a tab in ops_gui.py as well as hosted standalone by
    CorrelateAdPvsWindow below - same split PVLoggerPanel/PVLoggerWindow
    already use."""

    BEAMLINES = ["s1", "s20"]

    def __init__(self, config_path, parent=None, show_font_control=True):
        super().__init__(parent)
        self.config_path = config_path
        self.base_config_dir = os.path.dirname(config_path)
        self.cfg = pl.load_config(config_path)
        self.current_beamline = "s1"
        self.ad_files = []
        self._worker_thread = None  # (QThread, _CorrelateWorker), kept alive while a run is in progress

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QtWidgets.QToolBar()
        layout.addWidget(toolbar)
        toolbar.addWidget(QtWidgets.QLabel(" Beamline (for PV groups): "))
        self.beamline_combo = QtWidgets.QComboBox()
        self.beamline_combo.addItems(self.BEAMLINES)
        self.beamline_combo.currentTextChanged.connect(self._on_beamline_changed)
        toolbar.addWidget(self.beamline_combo)

        if show_font_control:
            toolbar.addSeparator()
            toolbar.addWidget(QtWidgets.QLabel(" Font size: "))
            self.font_size_spin = QtWidgets.QSpinBox()
            self.font_size_spin.setRange(6, 24)
            self.font_size_spin.setValue(DEFAULT_FONT_SIZE)
            self.font_size_spin.valueChanged.connect(self.set_font_size)
            toolbar.addWidget(self.font_size_spin)

        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        # PV logger CSV
        self.csv_edit = QtWidgets.QLineEdit()
        self.csv_edit.editingFinished.connect(self._maybe_autodetect_beamline)
        csv_browse = QtWidgets.QPushButton("Browse...")
        csv_browse.clicked.connect(self._browse_csv)
        csv_row = QtWidgets.QHBoxLayout()
        csv_row.addWidget(self.csv_edit)
        csv_row.addWidget(csv_browse)
        form.addRow("PV logger CSV:", csv_row)

        # Area-detector files
        self.files_list = QtWidgets.QListWidget()
        self.files_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.files_list.setMaximumHeight(100)
        add_files_btn = QtWidgets.QPushButton("Add files...")
        add_files_btn.clicked.connect(self._add_files)
        remove_files_btn = QtWidgets.QPushButton("Remove selected")
        remove_files_btn.clicked.connect(self._remove_selected_files)
        clear_files_btn = QtWidgets.QPushButton("Clear")
        clear_files_btn.clicked.connect(self._clear_files)
        files_btn_col = QtWidgets.QVBoxLayout()
        files_btn_col.addWidget(add_files_btn)
        files_btn_col.addWidget(remove_files_btn)
        files_btn_col.addWidget(clear_files_btn)
        files_btn_col.addStretch()
        files_row = QtWidgets.QHBoxLayout()
        files_row.addWidget(self.files_list, 1)
        files_row.addLayout(files_btn_col)
        form.addRow("Area-detector files:", files_row)

        # PV groups
        group_filter_row = QtWidgets.QHBoxLayout()
        self.group_filter_edit = QtWidgets.QLineEdit()
        self.group_filter_edit.setPlaceholderText("Filter groups...")
        self.group_filter_edit.textChanged.connect(self._apply_group_filter)
        check_all_btn = QtWidgets.QPushButton("Check All")
        check_all_btn.clicked.connect(lambda: self._set_visible_groups_checked(True))
        uncheck_all_btn = QtWidgets.QPushButton("Uncheck All")
        uncheck_all_btn.clicked.connect(lambda: self._set_visible_groups_checked(False))
        group_filter_row.addWidget(self.group_filter_edit)
        group_filter_row.addWidget(check_all_btn)
        group_filter_row.addWidget(uncheck_all_btn)

        self.groups_list = QtWidgets.QListWidget()
        self.groups_list.setMaximumHeight(140)
        groups_col = QtWidgets.QVBoxLayout()
        groups_col.addLayout(group_filter_row)
        groups_col.addWidget(self.groups_list)
        form.addRow("PV groups:", groups_col)
        self._rebuild_groups_list()

        # Explicit PV names, for anything not covered by a whole group
        self.extra_pvs_edit = QtWidgets.QLineEdit()
        self.extra_pvs_edit.setPlaceholderText("Additional PV names (comma/space-separated, must match CSV column headers)")
        form.addRow("Additional PVs:", self.extra_pvs_edit)

        # Mode - checkboxes rather than radio buttons: both can run in one
        # pass (each file's timestamps/interpolated PV values are computed
        # once and reused for whichever outputs are requested), not an
        # either/or choice.
        self.per_frame_check = QtWidgets.QCheckBox("Per-frame (one CSV per file, one row per frame)")
        self.averaged_check = QtWidgets.QCheckBox("Averaged (one combined CSV, one row per file)")
        self.per_frame_check.setChecked(True)
        self.per_frame_check.toggled.connect(self._on_mode_changed)
        self.averaged_check.toggled.connect(self._on_mode_changed)
        mode_col = QtWidgets.QVBoxLayout()
        mode_col.addWidget(self.per_frame_check)
        mode_col.addWidget(self.averaged_check)
        form.addRow("Mode:", mode_col)

        # Output - one row per mode, only the active one visible
        self.out_dir_edit = QtWidgets.QLineEdit()
        self.out_dir_edit.setPlaceholderText("(default: next to each input file)")
        out_dir_browse = QtWidgets.QPushButton("Browse...")
        out_dir_browse.clicked.connect(self._browse_out_dir)
        self.out_dir_row = QtWidgets.QWidget()
        out_dir_layout = QtWidgets.QHBoxLayout(self.out_dir_row)
        out_dir_layout.setContentsMargins(0, 0, 0, 0)
        out_dir_layout.addWidget(self.out_dir_edit)
        out_dir_layout.addWidget(out_dir_browse)
        form.addRow("Output directory:", self.out_dir_row)

        self.out_file_edit = QtWidgets.QLineEdit()
        out_file_browse = QtWidgets.QPushButton("Browse...")
        out_file_browse.clicked.connect(self._browse_out_file)
        self.out_file_row = QtWidgets.QWidget()
        out_file_layout = QtWidgets.QHBoxLayout(self.out_file_row)
        out_file_layout.setContentsMargins(0, 0, 0, 0)
        out_file_layout.addWidget(self.out_file_edit)
        out_file_layout.addWidget(out_file_browse)
        self.out_file_row.setVisible(False)
        form.addRow("Output CSV:", self.out_file_row)

        # Advanced HDF5 overrides - defaults are only a best guess (see
        # correlate_ad_pvs.py's own DEFAULT_TIMESTAMP_ATTR_CANDIDATES
        # comment), so these need to be easy to reach and override.
        self.timestamp_attr_edit = QtWidgets.QLineEdit()
        self.timestamp_attr_edit.setPlaceholderText("(default: try misc/NDArrayTimeStamp and a few others)")
        inspect_btn = QtWidgets.QPushButton("Inspect a file...")
        inspect_btn.clicked.connect(self._inspect_file)
        attr_row = QtWidgets.QHBoxLayout()
        attr_row.addWidget(self.timestamp_attr_edit)
        attr_row.addWidget(inspect_btn)
        form.addRow("Timestamp attribute:", attr_row)

        self.dataset_path_edit = QtWidgets.QLineEdit()
        self.dataset_path_edit.setPlaceholderText(f"(default: {cap.DEFAULT_DATASET_PATH})")
        form.addRow("Image dataset path:", self.dataset_path_edit)

        # Offline-gap threshold - if a numeric PV's nearest real sample is
        # farther than this from a frame's time (mid-run outage or a
        # permanent drop), that frame gets OFFLINE instead of a numeric
        # guess. Left blank by default: correlate_ad_pvs.py infers a
        # threshold from the CSV's own median logging interval.
        self.max_gap_edit = QtWidgets.QLineEdit()
        self.max_gap_edit.setPlaceholderText(f"(default: {cap.DEFAULT_MAX_GAP_MULTIPLIER}x the CSV's median logging interval)")
        self.max_gap_edit.setValidator(QtGui.QDoubleValidator(0.0, 1e12, 3, self.max_gap_edit))
        form.addRow("Max gap before OFFLINE (sec):", self.max_gap_edit)

        run_btn = QtWidgets.QPushButton("Run")
        run_btn.clicked.connect(self._run)
        layout.addWidget(run_btn)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        self.status_bar = QtWidgets.QStatusBar()
        layout.addWidget(self.status_bar)

        self.set_font_size(DEFAULT_FONT_SIZE)

    # -- beamline / group list -------------------------------------------------

    def _on_beamline_changed(self, beamline_name):
        self.current_beamline = beamline_name
        config_file = os.path.join(self.base_config_dir, f"pv_master_list_{beamline_name}.json")
        if os.path.exists(config_file):
            try:
                self.cfg = pl.load_config(config_file)
                self.config_path = config_file
                self.status_bar.showMessage(f"Switched to {beamline_name}")
            except Exception as e:
                self.status_bar.showMessage(f"Error loading {beamline_name} config: {str(e)}")
                self.cfg = pl.load_config(self.config_path)
        else:
            self.cfg = pl.load_config(self.config_path)
            self.status_bar.showMessage(f"Using default PV list for {beamline_name}")
        self._rebuild_groups_list()

    def _rebuild_groups_list(self):
        self.groups_list.clear()
        for group in pl.get_all_devices(self.cfg.get("pvs", [])):
            item = QtWidgets.QListWidgetItem(group)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.groups_list.addItem(item)

    def _apply_group_filter(self, text):
        text = text.lower()
        for row in range(self.groups_list.count()):
            item = self.groups_list.item(row)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _set_visible_groups_checked(self, checked):
        state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
        for row in range(self.groups_list.count()):
            item = self.groups_list.item(row)
            if not item.isHidden():
                item.setCheckState(state)

    def selected_groups(self):
        return [
            self.groups_list.item(row).text()
            for row in range(self.groups_list.count())
            if self.groups_list.item(row).checkState() == QtCore.Qt.Checked
        ]

    # -- file pickers -----------------------------------------------------------

    def _browse_csv(self):
        path = plg._choose_open_file(self, "Select PV logger CSV", filter_str="CSV files (*.csv);;All files (*)")
        if path:
            self.csv_edit.setText(path)
            self._maybe_autodetect_beamline()

    def _add_files(self):
        start_dir = os.path.dirname(self.ad_files[-1]) if self.ad_files else ""
        paths = _choose_open_files(self, "Select area-detector HDF5 files", start_dir)
        for path in paths:
            if path not in self.ad_files:
                self.ad_files.append(path)
                self.files_list.addItem(path)
        if paths:
            self._maybe_autodetect_beamline()

    def _maybe_autodetect_beamline(self):
        """Switch the beamline selector to match the CSV/AD file path,
        when it clearly names one - see _guess_beamline_from_path. Never
        overrides a selection that already agrees, and never guesses
        from nothing (an ambiguous or beamline-less path leaves the
        current selection alone)."""
        guess = _guess_beamline_from_path(self.csv_edit.text().strip())
        if guess is None and self.ad_files:
            guess = _guess_beamline_from_path(self.ad_files[0])
        if guess and guess in self.BEAMLINES and guess != self.current_beamline:
            self.beamline_combo.setCurrentText(guess)  # triggers _on_beamline_changed, which sets its own status message
            self.status_bar.showMessage(f"Auto-detected beamline '{guess}' from the file path - switched PV groups accordingly.")

    def _remove_selected_files(self):
        for item in self.files_list.selectedItems():
            self.ad_files.remove(item.text())
            self.files_list.takeItem(self.files_list.row(item))

    def _clear_files(self):
        self.ad_files = []
        self.files_list.clear()

    def _browse_out_dir(self):
        path = _choose_directory(self, "Select output directory")
        if path:
            self.out_dir_edit.setText(path)

    def _browse_out_file(self):
        path = plg._choose_save_file(self, "Select output CSV", filter_str="CSV files (*.csv);;All files (*)")
        if path:
            self.out_file_edit.setText(path)

    def _on_mode_changed(self, *_args):
        self.out_dir_row.setVisible(self.per_frame_check.isChecked())
        self.out_file_row.setVisible(self.averaged_check.isChecked())

    # -- inspect ------------------------------------------------------------

    def _inspect_file(self):
        start_dir = os.path.dirname(self.ad_files[-1]) if self.ad_files else ""
        path = plg._choose_open_file(self, "Select an HDF5 file to inspect", start_dir,
                                      filter_str="HDF5 files (*.h5 *.hdf5);;All files (*)")
        if not path:
            return
        try:
            attrs = cap.list_nd_attributes(path)
        except Exception as e:
            plg._message_box(QtWidgets.QMessageBox.Critical, self, "Inspect failed", str(e))
            return
        if not attrs:
            text = (f"No NDAttribute datasets found under 'misc' or "
                    f"'/entry/instrument/NDAttributes' in:\n{path}\n\n"
                    "This file may use a different HDF5 layout - falling back "
                    "to file mtime is the only option unless you know the "
                    "right dataset path to set below.")
        else:
            text = f"NDAttribute datasets found in:\n{path}\n\n" + "\n".join(attrs) + \
                "\n\nCopy one of these into the Timestamp attribute field above to use it."
        _show_text_dialog(self, "Inspect HDF5 file", text)

    # -- run ------------------------------------------------------------------

    def _run(self):
        csv_path = self.csv_edit.text().strip()
        if not csv_path:
            plg._message_box(QtWidgets.QMessageBox.Warning, self, "Missing input", "Select a PV logger CSV first.")
            return
        if not self.ad_files:
            plg._message_box(QtWidgets.QMessageBox.Warning, self, "Missing input", "Add at least one area-detector file.")
            return

        modes = []
        if self.per_frame_check.isChecked():
            modes.append("per-frame")
        if self.averaged_check.isChecked():
            modes.append("averaged")
        if not modes:
            plg._message_box(QtWidgets.QMessageBox.Warning, self, "Missing input",
                              "Check at least one mode (per-frame and/or averaged).")
            return

        out_dir = self.out_dir_edit.text().strip()
        out_path = self.out_file_edit.text().strip()
        if "averaged" in modes and not out_path:
            plg._message_box(QtWidgets.QMessageBox.Warning, self, "Missing input", "Choose an output CSV for averaged mode.")
            return

        pv_names = [name for name in self.extra_pvs_edit.text().replace(",", " ").split() if name]
        groups = self.selected_groups()
        if not pv_names and not groups:
            plg._message_box(QtWidgets.QMessageBox.Warning, self, "Missing input",
                              "Check at least one PV group or enter an additional PV name.")
            return

        max_gap_text = self.max_gap_edit.text().strip()
        max_gap_sec = float(max_gap_text) if max_gap_text else None

        self.log_view.clear()
        self.status_bar.showMessage("Running...")

        thread = QtCore.QThread(self)
        worker = _CorrelateWorker(
            modes, self.config_path, pv_names, groups, list(self.ad_files), csv_path,
            self.timestamp_attr_edit.text().strip(), self.dataset_path_edit.text().strip(),
            out_dir, out_path, max_gap_sec,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.log_view.appendPlainText)
        worker.finished.connect(self._on_run_finished)
        worker.error.connect(self._on_run_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._worker_thread = (thread, worker)
        thread.start()

    def _on_run_finished(self, message):
        self._worker_thread = None
        self.status_bar.showMessage(message)
        self.log_view.appendPlainText(message)

    def _on_run_error(self, message):
        self._worker_thread = None
        self.status_bar.showMessage(f"Failed: {message}")
        self.log_view.appendPlainText(f"ERROR: {message}")
        plg._message_box(QtWidgets.QMessageBox.Critical, self, "Run failed", message)

    # -- misc -----------------------------------------------------------------

    def set_font_size(self, size):
        font = QtWidgets.QApplication.instance().font()
        font.setPointSize(size)
        QtWidgets.QApplication.instance().setFont(font)
        for toolbar in self.findChildren(QtWidgets.QToolBar):
            toolbar.setFont(font)
            for widget in toolbar.findChildren(QtWidgets.QWidget):
                widget.setFont(font)


class CorrelateAdPvsWindow(QtWidgets.QMainWindow):
    """Standalone window hosting CorrelateAdPvsPanel - used when this file
    is run directly rather than embedded as a tab in ops_gui.py."""

    def __init__(self, config_path):
        super().__init__()
        self.setWindowTitle("PV/AD Matcher")
        self.resize(800, 700)
        self.panel = CorrelateAdPvsPanel(config_path)
        self.setCentralWidget(self.panel)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="PV/AD Matcher GUI")
    parser.add_argument("--config", default=pl.DEFAULT_CONFIG_PATH, help="Path to master PV list JSON")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = CorrelateAdPvsWindow(args.config)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
