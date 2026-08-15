#!/usr/bin/env python3
"""
Portable, auto-discovering EPICS PV logger for beamline status tracking.

Given a master list of every PV ever used across experimental setups
(pv_master_list.json), this tool probes which ones are actually online for
the current experiment, logs only those to a wide time-series CSV on an
interval, and alerts (email) if a PV that was online drops offline mid-run.

No dependency on APSpy/SPEC - only pyepics + the standard library, so this
works the same way regardless of which beamline/host it's run from.

Subcommands
-----------
list-pvs  Probe the master list and print an ONLINE/OFFLINE report. No logging.
start     Discover, then log on an interval until Ctrl-C.

Usage examples
--------------
  python pv_logger.py list-pvs --config pv_master_list.json
  python pv_logger.py start --config pv_master_list.json --outfile ./logs/run1.csv
  python pv_logger.py start --config pv_master_list.json --outfile /tmp/t.csv --interval 5 --dry-run
"""

import argparse
import json
import os
import smtplib
import socket
import sys
import time
from email.mime.text import MIMEText

try:
    import epics
except ImportError:
    sys.exit(
        "pyepics is required but is not installed.\n"
        "Install it with:  pip install pyepics\n"
        "(it's included in the shared 'ops' conda environment; see ../../environment.yml)"
    )

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "pv_master_list_s1.json")
DEFAULT_STATE_PATH = os.path.join(SCRIPT_DIR, "pv_alert_state.json")

OFFLINE_MARKER = "OFFLINE"

_DEFAULT_SETTINGS = {
    "log_interval_sec": 5,
    "connect_timeout_sec": 2.0,
    "recipients": [],
    "sender": "pv_logger@{host}".format(host=socket.gethostname()),
    "smtp_host": "apsmail.aps.anl.gov",
    "smtp_port": 25,
    "alert_cooldown_min": 60,
    "state_file": DEFAULT_STATE_PATH,
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path=DEFAULT_CONFIG_PATH):
    with open(path) as f:
        cfg = json.load(f)

    settings = dict(_DEFAULT_SETTINGS)
    settings.update(cfg.get("settings", {}))
    cfg["settings"] = settings
    cfg.setdefault("pvs", [])
    return cfg


def save_config(cfg, path):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Device Management
# ---------------------------------------------------------------------------

def get_all_devices(pv_defs):
    """Extract all unique device groups from PV definitions.
    Returns sorted list of device names."""
    devices = set()
    for entry in pv_defs:
        group = entry.get("group")
        if group:
            devices.add(group)
    return sorted(devices)


def filter_pvs_by_devices(pv_defs, selected_devices):
    """Filter PV definitions to only those in selected device groups.
    Returns filtered list of PV definitions."""
    if not selected_devices:
        return []
    return [
        entry for entry in pv_defs
        if entry.get("group") in selected_devices
    ]


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_pvs(pv_defs, timeout_sec):
    """
    Probe every {name, pv} definition for connectivity, in parallel - total
    wall time is bounded by timeout_sec regardless of how many PVs end up
    offline (each epics.PV() kicks off an async CA search; we then poll all
    of them together instead of waiting out the full timeout serially per
    PV, which would be timeout_sec * offline_count).

    Returns (online: {name: epics.PV}, offline: [{name, pv, group}]).
    """
    pending = [
        (entry, epics.PV(entry["pv"], connection_timeout=timeout_sec, auto_monitor=True))
        for entry in pv_defs
    ]

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if all(pv_obj.connected for _, pv_obj in pending):
            break
        time.sleep(0.05)

    online = {}
    offline = []
    for entry, pv_obj in pending:
        if pv_obj.connected:
            online[entry["name"]] = pv_obj
        else:
            offline.append(entry)

    return online, offline


def format_discovery_report(online, offline):
    lines = ["{} of {} PVs online".format(len(online), len(online) + len(offline)), ""]
    for name in sorted(online):
        lines.append("  [ONLINE ] {:<40} {}".format(name, online[name].pvname))
    for entry in sorted(offline, key=lambda e: e["name"]):
        lines.append("  [OFFLINE] {:<40} {}".format(entry["name"], entry["pv"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def sample(online_pvs):
    """
    Read every PV that was online at discovery time.

    Returns (values: {name: value or OFFLINE_MARKER}, currently_offline:
    [name]) - currently_offline lists every PV that isn't connected right
    now, whether it just dropped or has been down since a prior cycle.
    """
    values = {}
    currently_offline = []
    for name, pv_obj in online_pvs.items():
        if pv_obj.connected:
            values[name] = pv_obj.get()
        else:
            values[name] = OFFLINE_MARKER
            currently_offline.append(name)
    return values, currently_offline


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_header(csv_path, names, device_selection=None):
    """Legacy-matching format (see APSpy_s1id/macros.py write_logging_header):
    trailing ', ' after every column including the last. Skipped if the file
    already exists, so `start` can be resumed against the same outfile.
    If device_selection is provided, write it as a comment for audit trail."""
    if os.path.exists(csv_path):
        return
    with open(csv_path, "w") as f:
        if device_selection:
            f.write("# Devices: {}\n".format(", ".join(device_selection)))
            f.write("# Timestamp: {}\n".format(time.ctime()))
        f.write("Date, ")
        for name in names:
            f.write(name + ", ")
        f.write("\n")


def write_row(csv_path, names, values, timestamp):
    row = [time.ctime(timestamp)] + [str(values.get(name, OFFLINE_MARKER)) for name in names]
    with open(csv_path, "a") as f:
        f.write(", ".join(row) + "\n")


def write_skipped_report(csv_path, offline):
    """Record which master-list PVs weren't online at discovery time, next
    to the CSV, so it's clear per-experiment what wasn't hooked up."""
    skipped_path = csv_path + ".skipped.txt"
    with open(skipped_path, "w") as f:
        f.write("PVs offline at discovery time (not logged this run):\n\n")
        for entry in sorted(offline, key=lambda e: e["name"]):
            f.write("{:<40} {}\n".format(entry["name"], entry["pv"]))
    return skipped_path


# ---------------------------------------------------------------------------
# Alerting
# ---------------------------------------------------------------------------

def _load_state(state_file):
    if not os.path.exists(state_file):
        return {}
    with open(state_file) as f:
        return json.load(f)


def _save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def send_drop_alert(cfg, dropped_names, csv_path, dry_run=False):
    settings = cfg["settings"]
    subject = "PV OFFLINE: {} on {}".format(", ".join(dropped_names), socket.gethostname())
    body = "\n".join(
        [
            "The following PV(s) were online at the start of this monitoring run",
            "but are now offline:",
            "",
        ]
        + ["  " + name for name in dropped_names]
        + ["", "Log file: {}".format(csv_path)]
    )

    if dry_run or not settings["recipients"]:
        print("--- {} email ---".format("DRY-RUN" if dry_run else "NO RECIPIENTS CONFIGURED"))
        print("Subject:", subject)
        print(body)
        print("-----------------------")
        return True

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings["sender"]
    msg["To"] = ", ".join(settings["recipients"])

    try:
        server = smtplib.SMTP(settings["smtp_host"], settings["smtp_port"], timeout=10)
        try:
            server.sendmail(settings["sender"], settings["recipients"], msg.as_string())
        finally:
            server.quit()
    except OSError as exc:
        print("Failed to send PV-drop alert email: {}".format(exc), file=sys.stderr)
        return False

    return True


def process_drop_alerts(cfg, currently_offline, csv_path, dry_run=False):
    """Alert on offline PVs, respecting a per-PV cooldown so a flapping PV
    doesn't send an email every cycle."""
    if not currently_offline:
        return []

    settings = cfg["settings"]
    state = _load_state(settings["state_file"])
    cooldown_sec = settings["alert_cooldown_min"] * 60
    now = time.time()

    to_alert = [name for name in currently_offline if (now - state.get(name, 0)) >= cooldown_sec]
    if not to_alert:
        return []

    if send_drop_alert(cfg, to_alert, csv_path, dry_run=dry_run):
        if not dry_run:
            for name in to_alert:
                state[name] = now
            _save_state(settings["state_file"], state)
        return to_alert

    return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_list_pvs(args):
    cfg = load_config(args.config)
    online, offline = discover_pvs(cfg["pvs"], cfg["settings"]["connect_timeout_sec"])
    print(format_discovery_report(online, offline))
    return 0


def cmd_start(args):
    cfg = load_config(args.config)
    if args.interval is not None:
        cfg["settings"]["log_interval_sec"] = args.interval

    print("Discovering PVs (timeout {}s)...".format(cfg["settings"]["connect_timeout_sec"]))
    online, offline = discover_pvs(cfg["pvs"], cfg["settings"]["connect_timeout_sec"])
    print(format_discovery_report(online, offline))

    if not online:
        print("No PVs online - nothing to log.", file=sys.stderr)
        return 1

    names = sorted(online)
    write_header(args.outfile, names)
    if offline:
        skipped_path = write_skipped_report(args.outfile, offline)
        print("Offline-at-start PVs recorded in: {}".format(skipped_path))

    if args.test_email:
        ok = send_drop_alert(cfg, [names[0]], args.outfile, dry_run=args.dry_run)
        return 0 if ok else 1

    interval = cfg["settings"]["log_interval_sec"]
    print("Logging every {}s to {}. Ctrl-C to stop.".format(interval, args.outfile))
    try:
        while True:
            now = time.time()
            values, currently_offline = sample(online)
            write_row(args.outfile, names, values, now)
            dropped = process_drop_alerts(cfg, currently_offline, args.outfile, dry_run=args.dry_run)
            if dropped:
                print("Alert sent for offline PV(s): {}".format(", ".join(dropped)))
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Auto-discovering EPICS PV logger.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to master PV list JSON")

    list_p = subparsers.add_parser("list-pvs", parents=[common], help="Probe PVs, print ONLINE/OFFLINE report")
    list_p.set_defaults(func=cmd_list_pvs)

    start_p = subparsers.add_parser("start", parents=[common], help="Discover, then log until Ctrl-C")
    start_p.add_argument("--outfile", required=True, help="CSV file to log to")
    start_p.add_argument("--interval", type=float, default=None, help="Override log_interval_sec")
    start_p.add_argument("--dry-run", action="store_true", help="Print alert emails instead of sending")
    start_p.add_argument("--test-email", action="store_true",
                          help="Force-send a test drop-alert for the first online PV")
    start_p.set_defaults(func=cmd_start)

    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
