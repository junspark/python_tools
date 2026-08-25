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
import json
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
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    sys.exit(
        "PyQt5 is required for the GUI but is not installed.\n"
        "Install it with:  pip install PyQt5\n"
    )


DEFAULT_FONT_SIZE = 10

# Remembers window size/position and font size across restarts. Deliberately
# separate from disk_monitor/pv_logger/data_integrity's own config files -
# font size and window geometry are properties of this combined shell, not
# of any one tool, and the three tabs' configs shouldn't need to agree on a
# single font size just because they happen to be viewed together here.
PREFS_PATH = os.path.join(SCRIPT_DIR, "ops_gui_prefs.json")


def _load_prefs():
    try:
        with open(PREFS_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_prefs(prefs):
    try:
        with open(PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
    except OSError:
        pass  # best-effort - a stale/unwritable prefs file shouldn't block using the GUI


class OpsGuiWindow(QtWidgets.QMainWindow):
    def __init__(self, disk_config, pv_config, di_config):
        super().__init__()
        self.setWindowTitle("Ops")

        self._prefs = _load_prefs()

        # Width/height only, deliberately not position: this same prefs
        # file is read from whatever computer you log in from (shared
        # home directory), and a saved absolute screen position (or
        # restoreGeometry()'s full blob, which bundles position and even
        # which screen) can land off-screen entirely on a different
        # monitor layout. Let the window manager place it; just remember
        # how big it was.
        width = self._prefs.get("width", 1000)
        height = self._prefs.get("height", 500)
        self.resize(width, height)

        # Explicit initial position, computed fresh every launch (never
        # persisted - see the comment above) from whatever screen this
        # launch actually has available - confirmed necessary on at least
        # one real deployment: a Wayland/Mutter compositor with an unusual
        # multi-monitor layout placed a brand-new, position-less top-level
        # window entirely off every monitor by default. An explicit
        # XMoveWindow issued after the window was already mapped was
        # silently overridden by the compositor, but a position requested
        # before the window is first shown is honored - Wayland compositors
        # generally only exercise their own placement heuristic when the
        # client hasn't already asked for somewhere specific.
        #
        # screenAt(cursor position), not primaryScreen(): confirmed
        # directly on a second real deployment (a different, "unusual"
        # multi-monitor arrangement - mixed sizes/offsets) that even this
        # fix's own primaryScreen()-based centering could land the window
        # somewhere unreachable, resurfacing the exact symptom this code
        # already exists to prevent. Since this is a brand-new top-level
        # window with no parent to anchor to, the mouse cursor's current
        # screen is the best available proxy for "the monitor the user is
        # actually looking at right now" - falls back to primaryScreen()
        # only if the cursor position doesn't resolve to any screen.
        screen = QtWidgets.QApplication.screenAt(QtGui.QCursor.pos()) or QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = avail.x() + max(0, (avail.width() - width) // 2)
            y = avail.y() + max(0, (avail.height() - height) // 2)
            # Clamp the whole rectangle inside avail, not just the
            # centering formula above - that formula alone still assumes
            # width/height <= avail's, which needn't hold on an unusually
            # small or oddly-shaped monitor.
            x = max(avail.x(), min(x, avail.x() + avail.width() - width))
            y = max(avail.y(), min(y, avail.y() + avail.height() - height))
            self.move(x, y)

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
        self.font_size_spin.setValue(self._prefs.get("font_size", DEFAULT_FONT_SIZE))
        self.font_size_spin.valueChanged.connect(self.set_font_size)
        toolbar.addWidget(self.font_size_spin)

        self.set_font_size(self.font_size_spin.value())

    def set_font_size(self, size):
        self.disk_panel.set_font_size(size)
        self.pv_panel.set_font_size(size)
        self.di_panel.set_font_size(size)
        self._prefs["font_size"] = size
        _save_prefs(self._prefs)

    def closeEvent(self, event):
        # Window size is only worth persisting once, on exit - saving on
        # every resize event would mean constant disk writes while the
        # user is just dragging the window.
        self._prefs["width"] = self.width()
        self._prefs["height"] = self.height()
        _save_prefs(self._prefs)
        super().closeEvent(event)


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
    # raise_()/activateWindow() in addition to show(): on a real remote
    # multi-monitor setup (SSH X11 forwarding to a Windows X server,
    # confirmed via a direct screen-geometry diagnostic), the window's
    # computed position was entirely correct and squarely inside the
    # primary monitor's bounds, yet it still didn't reliably come to the
    # front - show() alone maps the window, but doesn't request it be
    # raised above other windows or given input focus, and this display
    # setup is deliberately conservative about which clients get to do
    # that unprompted. Asking explicitly gives it the clearest possible
    # signal that this is a fresh, user-facing window that should come to
    # the front, rather than relying on whatever its default heuristic
    # does for a plain show(). Doesn't fully eliminate the flakiness on
    # this particular display pipeline (a relaunch can still occasionally
    # need a retry), but is the correct, standard thing to ask for either
    # way.
    window.raise_()
    window.activateWindow()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
