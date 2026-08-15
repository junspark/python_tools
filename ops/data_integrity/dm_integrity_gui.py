#!/usr/bin/env python3
"""
Data integrity GUI: PyQt5 panel for monitoring experiment upload integrity.
Dashboard view shows recent 10 experiments with file statistics and status.
"""

import json
import os
import sys
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
}


class _ScanWorker(QtCore.QObject):
    """Runs a Scan or Verify MD5 pass off the GUI thread - get_upload_status/
    get_catalog_files are SSH round-trips (seconds each) and verify_checksums
    reads every byte of every file, all of which would otherwise freeze the
    whole window (Qt's event loop is single-threaded)."""

    finished = QtCore.pyqtSignal(dict)
    error = QtCore.pyqtSignal(str)

    def __init__(self, exp_name, station_name, remote_host, remote_user, setup_script,
                 local_root, dataset, records_dir, do_checksums):
        super().__init__()
        self.exp_name = exp_name
        self.station_name = station_name
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.setup_script = setup_script
        self.local_root = local_root
        self.dataset = dataset
        self.records_dir = records_dir
        self.do_checksums = do_checksums

    def run(self):
        try:
            upload_status = di.get_upload_status(
                self.exp_name, self.station_name, self.remote_host, self.remote_user, self.setup_script)
            catalog_files = di.get_catalog_files(
                self.exp_name, self.dataset, self.station_name, self.remote_host, self.remote_user, self.setup_script)
            local_files = di.scan_local_files(self.local_root)
            comparison = di.compare(local_files, catalog_files)

            checksum_results = None
            if self.do_checksums:
                paths_to_verify = [p for p, s in comparison.items() if s == "MATCH"]
                checksum_results = di.verify_checksums(self.local_root, catalog_files, paths_to_verify)

            report = di.build_report(self.exp_name, upload_status, comparison, checksum_results)
            di.save_record(self.records_dir, self.exp_name, report)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))


class DataIntegrityPanel(QtWidgets.QWidget):
    def __init__(self, config_path, show_font_control=True):
        super().__init__()
        self.config_path = config_path
        self.config = {}
        self.show_font_control = show_font_control
        self.font_size = 10
        self.last_reports = {}
        self._row_buttons = {}
        self._active_workers = {}

        self._load_config()
        self._init_ui()

        # Auto-discover and populate experiments on startup
        self._discover_and_populate_experiments()

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
            "s1": "/home/beams/PARKJS/mnt/s1c",
            "s20": "/home/beams3/PARKJS/mnt/s20a",
        })
        per_beamline = settings.get("experiments_per_beamline", 3)

        try:
            # Dict order (s1 before s20, per the config file) gives us
            # "grouped by sector" for free; discover_local_experiments
            # already sorts each beamline's own results by recency.
            recent_exps = []
            for beamline, base_dir in local_bases.items():
                for exp_name, local_root in di.discover_local_experiments(base_dir, limit=per_beamline):
                    recent_exps.append((exp_name, beamline, local_root))
                    self._register_local_root(exp_name, local_root)

            if not recent_exps:
                self.status_label.setText("No experiment directories found under " + ", ".join(local_bases.values()))
                return

            # Switch to the 6-column layout (adds Beamline + History) - the
            # base table from _init_ui only has 5 columns, and
            # setHorizontalHeaderLabels does NOT grow columnCount on its own,
            # so without this the last two labels/widgets below (Actions
            # sliding to column 4, History needing column 5) would silently
            # never appear.
            self.table_widget.setColumnCount(6)
            self.table_widget.setHorizontalHeaderLabels([
                "Expid", "Beamline", "Upload Status", "Files", "Actions", "History"
            ])
            self.table_widget.setColumnWidth(1, 80)  # Beamline column
            self.table_widget.setColumnWidth(2, 120)  # Upload status
            self.table_widget.setColumnWidth(5, 100)  # History
            self.table_widget.setColumnWidth(4, 200)  # Actions (Scan + Verify MD5 buttons)

            self.table_widget.setRowCount(len(recent_exps))

            for row, (exp_name, beamline, local_root) in enumerate(recent_exps):
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
                verify_md5_btn = QtWidgets.QPushButton("Verify MD5")
                verify_md5_btn.clicked.connect(lambda checked, e=exp_name: self._on_verify_md5(e))
                buttons_layout.addWidget(scan_btn)
                buttons_layout.addWidget(verify_md5_btn)
                self._row_buttons[exp_name] = (scan_btn, verify_md5_btn)
                buttons_layout.setContentsMargins(0, 0, 0, 0)

                buttons_widget = QtWidgets.QWidget()
                buttons_widget.setLayout(buttons_layout)
                self.table_widget.setCellWidget(row, 4, buttons_widget)

                # History
                history_btn = QtWidgets.QPushButton("History")
                history_btn.clicked.connect(lambda checked, e=exp_name: self._on_history(e))
                self.table_widget.setCellWidget(row, 5, history_btn)

                # Deliberately NOT previewing DM status here: local_root is
                # now always known (that's the point of local discovery), so
                # an automatic preview would mean a real DM/SSH check for
                # every row on every startup. Checking against DM is Scan/
                # Verify MD5's job - explicit, on-demand, backgrounded.

            counts = {}
            for _, beamline, _ in recent_exps:
                counts[beamline] = counts.get(beamline, 0) + 1
            summary = ", ".join(f"{n} from {b}" for b, n in counts.items())
            self.status_label.setText(f"Loaded {summary} (from local s1c/s20a directories)")

        except Exception as e:
            self.status_label.setText(f"Error discovering experiments: {str(e)[:100]}")

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                self.config = json.load(f)
        else:
            self.config = {"settings": {}, "experiments": []}

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(QtWidgets.QLabel("Recent 10 experiments by expid:"))
        header_layout.addStretch()

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
        self.table_widget.setColumnWidth(0, 80)
        self.table_widget.setColumnWidth(1, 120)
        self.table_widget.setColumnWidth(2, 150)
        self.table_widget.setColumnWidth(3, 200)  # Actions (Scan + Verify MD5 buttons)
        self.table_widget.setColumnWidth(4, 100)

        layout.addWidget(self.table_widget)

        self.status_label = QtWidgets.QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _refresh_experiment_list(self):
        if di is None:
            self.status_label.setText("ERROR: dm module not available (source dm.setup.sh first)")
            return

        experiments = self.config.get("experiments", [])
        if not experiments:
            self.table_widget.setRowCount(0)
            self.status_label.setText("No experiments configured")
            return

        sorted_exps = sorted(experiments, key=lambda e: e.get("name", ""), reverse=True)
        recent_exps = sorted_exps[:10]

        self.table_widget.setRowCount(len(recent_exps))

        for row, exp_config in enumerate(recent_exps):
            exp_name = exp_config.get("name", "")
            is_running = exp_config.get("running", False)

            exp_id_item = QtWidgets.QTableWidgetItem(exp_name)
            if is_running:
                font = exp_id_item.font()
                font.setBold(True)
                exp_id_item.setFont(font)

            self.table_widget.setItem(row, 0, exp_id_item)

            upload_status_item = QtWidgets.QTableWidgetItem("---")
            self.table_widget.setItem(row, 1, upload_status_item)

            files_item = QtWidgets.QTableWidgetItem("---")
            self.table_widget.setItem(row, 2, files_item)

            buttons_layout = QtWidgets.QHBoxLayout()
            scan_btn = QtWidgets.QPushButton("Scan")
            scan_btn.clicked.connect(lambda checked, e=exp_name: self._on_scan(e))
            verify_md5_btn = QtWidgets.QPushButton("Verify MD5")
            verify_md5_btn.clicked.connect(lambda checked, e=exp_name: self._on_verify_md5(e))
            buttons_layout.addWidget(scan_btn)
            buttons_layout.addWidget(verify_md5_btn)
            self._row_buttons[exp_name] = (scan_btn, verify_md5_btn)
            buttons_layout.setContentsMargins(0, 0, 0, 0)

            buttons_widget = QtWidgets.QWidget()
            buttons_widget.setLayout(buttons_layout)
            self.table_widget.setCellWidget(row, 3, buttons_widget)

            history_btn = QtWidgets.QPushButton("History")
            history_btn.clicked.connect(lambda checked, e=exp_name: self._on_history(e))
            self.table_widget.setCellWidget(row, 4, history_btn)

            self._update_experiment_row(row, exp_name)

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
        """Return (remote_host, remote_user, setup_script) for beamline, so
        get_upload_status/get_catalog_files reach the right beamline's DM
        instance over SSH instead of silently falling back to local
        execution (which returns empty/error results on any host without a
        local dm install - not the beamline's actual upload status).
        Mirrors the per-station config discovery used to build for
        get_recent_experiments before discovery moved to local s1c/s20a
        scanning.
        """
        settings = self.config.get("settings", {})
        remote_hosts = settings.get("remote_hosts", {})
        setup_scripts = settings.get("setup_scripts", {})
        beamline_defaults = {
            "s1": ("egressy", "s1iduser", "~/bin/dm_setup_1id.sh dm"),
            "s20": ("zion", "s20iduser", "~/bin/dm_setup_20ide.sh"),
        }
        default_host, default_user, default_script = beamline_defaults.get(beamline, (None, None, "/dm/1id/etc/dm.setup.sh"))
        remote_host = remote_hosts.get(beamline, default_host)
        setup_script = setup_scripts.get(beamline, default_script)
        return remote_host, default_user, setup_script

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
            candidate = template.format(expid=exp_name)
            if os.path.isdir(candidate):
                return candidate

        if not allow_prompt:
            return None

        start_dir = os.path.dirname(template.format(expid=exp_name)) if template else ""
        chosen = QtWidgets.QFileDialog.getExistingDirectory(
            self, f"Select local data folder for '{exp_name}'", start_dir)
        return chosen or None

    def _update_experiment_row(self, row, exp_name, beamline=None, local_root=None):
        """Refresh one row's Upload Status/Files cells.

        local_root: pass this when the caller already resolved it (e.g.
        _on_scan/_on_verify_md5, via the full explicit-config -> convention
        -> prompt resolution) - re-deriving it here would fail for a
        convention-path or picker-chosen root, since the automatic/silent
        callers of this method deliberately skip both of those (see
        _resolve_local_root's docstring).
        """
        if di is None:
            return

        # 5-column (offline/manual) layout: Expid, Upload Status, Files,
        # Actions, History. 6-column (auto-discovery) layout adds Beamline
        # between Expid and Upload Status, shifting everything after it by 1.
        six_col = self.table_widget.columnCount() >= 6
        status_col, files_col = (2, 3) if six_col else (1, 2)

        settings = self.config.get("settings", {})
        records_dir = settings.get("records_dir", di.DEFAULT_RECORDS_DIR)
        station_name = settings.get("station_name", "SOJOURNER")
        remote_host, remote_user, setup_script = self._remote_info_for_beamline(beamline)

        if local_root is None:
            local_root = self._resolve_local_root(exp_name, beamline, try_convention=False, allow_prompt=False)
        if not local_root:
            return

        exp_config = None
        for exp in self.config.get("experiments", []):
            if exp.get("name") == exp_name:
                exp_config = exp
                break
        dataset = exp_config.get("dataset") if exp_config else None

        try:
            upload_status = di.get_upload_status(exp_name, station_name, remote_host, remote_user, setup_script)
            catalog_files = di.get_catalog_files(exp_name, dataset, station_name, remote_host, remote_user, setup_script)
            local_files = di.scan_local_files(local_root)
            comparison = di.compare(local_files, catalog_files)

            report = di.build_report(exp_name, upload_status, comparison)
            self.last_reports[exp_name] = report

            file_stats = report["file_stats"]
            good_count = file_stats["good"]
            bad_count = file_stats["bad"]
            sojourner_status = report["sojourner_status"]

            upload_status_item = QtWidgets.QTableWidgetItem(sojourner_status.replace("_", " ").title())
            upload_status_item.setToolTip(report["sojourner_summary"])
            self.table_widget.setItem(row, status_col, upload_status_item)

            files_text = f"{good_count} good / {bad_count} bad"
            files_item = QtWidgets.QTableWidgetItem(files_text)

            if sojourner_status == "FULLY_LANDED" and upload_status.get("upload_complete", False):
                bg_color = STATUS_COLORS["good"]
            elif file_stats["size_mismatch"] > 0 or file_stats["remote_only"] > 0 or file_stats["checksum_mismatch"] > 0:
                # A real integrity problem (not just "hasn't uploaded yet").
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

        except Exception as e:
            status_item = QtWidgets.QTableWidgetItem(f"Error: {str(e)[:30]}")
            self.table_widget.setItem(row, status_col, status_item)

    def _on_scan(self, exp_name):
        self._run_scan_or_verify(exp_name, do_checksums=False)

    def _on_verify_md5(self, exp_name):
        self._run_scan_or_verify(exp_name, do_checksums=True)

    def _set_row_buttons_enabled(self, exp_name, enabled):
        buttons = self._row_buttons.get(exp_name)
        if buttons:
            for btn in buttons:
                btn.setEnabled(enabled)

    def _run_scan_or_verify(self, exp_name, do_checksums):
        verb = "Verifying checksums for" if do_checksums else "Running lightweight scan for"
        action = "Verification" if do_checksums else "Scan"

        if di is None:
            self.status_label.setText("ERROR: dm module not available")
            return

        if exp_name in self._active_workers:
            self.status_label.setText(f"{action} already running for '{exp_name}'")
            return

        # Resolving local_root can pop a folder picker (QFileDialog), which
        # must happen on the GUI thread - do this before handing off to the
        # background worker, not inside it.
        beamline = self._beamline_for_exp(exp_name)
        local_root = self._resolve_local_root(exp_name, beamline, try_convention=True, allow_prompt=True)
        if not local_root:
            self.status_label.setText(f"{action} cancelled: no local folder selected for '{exp_name}'")
            return

        exp_config = None
        for exp in self.config.get("experiments", []):
            if exp.get("name") == exp_name:
                exp_config = exp
                break
        dataset = exp_config.get("dataset") if exp_config else None

        settings = self.config.get("settings", {})
        records_dir = settings.get("records_dir", di.DEFAULT_RECORDS_DIR)
        station_name = settings.get("station_name", "SOJOURNER")
        remote_host, remote_user, setup_script = self._remote_info_for_beamline(beamline)

        self.status_label.setText(f"{verb} '{exp_name}' (running in background)...")
        self._set_row_buttons_enabled(exp_name, False)

        thread = QtCore.QThread(self)
        worker = _ScanWorker(exp_name, station_name, remote_host, remote_user, setup_script,
                              local_root, dataset, records_dir, do_checksums)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(
            lambda report: self._on_worker_finished(exp_name, beamline, local_root, do_checksums, report))
        worker.error.connect(lambda msg: self._on_worker_error(exp_name, action, msg))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        # Keep references alive - nothing else holds them, and a GC'd thread
        # object mid-run silently kills the worker.
        self._active_workers[exp_name] = (thread, worker)
        thread.start()

    def _on_worker_finished(self, exp_name, beamline, local_root, do_checksums, report):
        self._active_workers.pop(exp_name, None)
        self._set_row_buttons_enabled(exp_name, True)
        self.last_reports[exp_name] = report

        file_stats = report["file_stats"]
        verb = "Checksum verification" if do_checksums else "Scan"
        msg = f"{verb} complete: {report['sojourner_summary']} ({file_stats['good']} good / {file_stats['bad']} bad)"
        if report["recommend_deletion"]:
            msg += " - SAFE TO DELETE"
        self.status_label.setText(msg)

        for row in range(self.table_widget.rowCount()):
            if self.table_widget.item(row, 0).text() == exp_name:
                self._update_experiment_row(row, exp_name, beamline, local_root=local_root)
                break

    def _on_worker_error(self, exp_name, action, msg):
        self._active_workers.pop(exp_name, None)
        self._set_row_buttons_enabled(exp_name, True)
        self.status_label.setText(f"{action} failed: {msg}")

    def _on_history(self, exp_name):
        if di is None:
            QtWidgets.QMessageBox.critical(self, "Error", "dm module not available")
            return

        settings = self.config.get("settings", {})
        records_dir = settings.get("records_dir", di.DEFAULT_RECORDS_DIR)

        records = di.list_records(records_dir, exp_name)
        if not records:
            QtWidgets.QMessageBox.information(self, "History", f"No records found for '{exp_name}'")
            return

        msg = f"Records for '{exp_name}':\n\n"
        for timestamp, filepath in records[-10:]:
            with open(filepath) as f:
                record = json.load(f)
            stats = record["file_stats"]
            import time
            rec_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            msg += f"{rec_time}: {stats['good']} good / {stats['bad']} bad\n"

        QtWidgets.QMessageBox.information(self, "History", msg)

    def set_font_size(self, size):
        self.font_size = size
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self.table_widget.setFont(font)


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
