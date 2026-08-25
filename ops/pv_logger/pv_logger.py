#!/usr/bin/env python3
"""
Portable, auto-discovering EPICS PV logger for beamline status tracking.

Given a master list of every PV ever used across experimental setups
(pv_master_list.json), this tool probes which ones are actually online for
the current experiment, logs only those to a wide time-series CSV on an
interval, and alerts (email) if a PV that was online drops offline mid-run.

No pyepics dependency - reads PVs by shelling out to the `caget` CLI
(EPICS Base, e.g. the facility-wide /APSshare/epics install) via a bounded
thread pool, one process per PV. This is deliberate, not a stopgap: neither
egressy nor zion (the hosts this tool's persistent jobs actually run on -
see pv_logger_gui.py) have a working pyepics install or internet access to
get one, and a single `caget` call given multiple PV names prints nothing
at all for any of them if even one times out (confirmed directly) - unsafe
for this tool's normal "some online, some not" operating condition. See
settings.caget_path.

Subcommands
-----------
list-pvs  Probe the master list and print an ONLINE/OFFLINE report. No logging.
start     Discover, then log on an interval until Ctrl-C (or SIGTERM, e.g.
          `systemctl --user stop` on a detached job - see --status-file).

Usage examples
--------------
  python pv_logger.py list-pvs --config pv_master_list.json
  python pv_logger.py start --config pv_master_list.json --outfile ./logs/run1.csv
  python pv_logger.py start --config pv_master_list.json --outfile /tmp/t.csv --interval 5 --dry-run
"""

import argparse
import json
import os
import signal
import smtplib
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
import remote_job as rj

DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "pv_master_list_s1.json")
DEFAULT_STATE_PATH = os.path.join(SCRIPT_DIR, "pv_alert_state.json")
# The facility-wide shared EPICS Base install (identical mount on every
# beamline host, confirmed on both egressy and zion) - not a per-account
# install, so no setup/activation step is needed before this tool runs.
DEFAULT_CAGET_PATH = "/APSshare/epics/base-7.0.10/bin/rhel9-x86_64/caget"
MAX_CAGET_WORKERS = 64

OFFLINE_MARKER = "OFFLINE"

_DEFAULT_SETTINGS = {
    "log_interval_sec": 5,
    "connect_timeout_sec": 2.0,
    "caget_path": DEFAULT_CAGET_PATH,
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
# Persistent remote job routing (pv_logger_gui.py launches this CLI's own
# `start` subcommand as a detached systemd --user job on settings.remote_job's
# host/user - the actual caget/writing runs there, not wherever the GUI is)
# ---------------------------------------------------------------------------

def pv_logger_status_dir(remote_base):
    return os.path.join(remote_base, "status")


def pv_logger_status_path(remote_base, beamline):
    return os.path.join(pv_logger_status_dir(remote_base), f"{beamline}.json")


def pv_logger_unit_name(beamline):
    """Deterministic systemd --user unit name for beamline's PV-logging job
    - one per beamline (not per-experiment, unlike checksum jobs), since
    only one logger should ever run per beamline at a time."""
    return rj.systemd_unit_name("pv-logger@.service", beamline)


# Thin pass-throughs so pv_logger_gui.py only ever needs `import pv_logger
# as pl` (matching dm_integrity.py's own convention) rather than also
# importing remote_job directly.
canonical_path = rj.canonical_path
lock_dir = rj.lock_dir
acquire_remote_lock = rj.acquire_remote_lock
release_remote_lock = rj.release_remote_lock
write_remote_file = rj.write_remote_file
launch_detached_job = rj.launch_detached_job
run_shell_command = rj.run_shell_command


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _caget_one(caget_path, pv_name, timeout_sec):
    """Read one PV via a single `caget -t` subprocess call - terse mode
    (value only, no echoed name) so there's nothing to strip/parse beyond
    the trailing newline. Returns the value string, or None if the PV
    didn't respond within timeout_sec (nonzero exit, e.g. "Channel connect
    timed out") or the process itself couldn't be run.

    Deliberately one process per PV rather than batching multiple PV names
    into a single caget call: confirmed directly that a mixed batch (some
    online, some not) prints nothing at all for *any* of them once even one
    PV in that call times out - unsafe given this tool's normal "some
    online, some offline" operating condition.
    """
    try:
        result = subprocess.run(
            [caget_path, "-t", "-w", str(timeout_sec), pv_name],
            capture_output=True, text=True, timeout=timeout_sec + 2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value if value else None


def _caget_many(caget_path, pv_by_name, timeout_sec):
    """Read many PVs concurrently, each via its own _caget_one call in a
    bounded thread pool - total wall time is bounded by timeout_sec
    regardless of how many end up offline, the same property the old
    pyepics-based implementation had via async connection objects, just
    achieved with subprocess calls instead of persistent CA monitors.
    Returns {name: value_or_None}.
    """
    if not pv_by_name:
        return {}
    with ThreadPoolExecutor(max_workers=min(MAX_CAGET_WORKERS, len(pv_by_name))) as pool:
        futures = {
            name: pool.submit(_caget_one, caget_path, pv_name, timeout_sec)
            for name, pv_name in pv_by_name.items()
        }
        return {name: future.result() for name, future in futures.items()}


def discover_pvs(pv_defs, timeout_sec, caget_path=DEFAULT_CAGET_PATH):
    """
    Probe every {name, pv} definition for connectivity, in parallel via a
    bounded thread pool of `caget` calls - total wall time is bounded by
    timeout_sec regardless of how many PVs end up offline.

    Returns (online: {name: entry}, offline: [entry, ...]) - online's
    values are the plain PV-definition dicts ({name, pv, group}), not live
    connection objects: there's no persistent connection to hold with this
    approach, every read is an independent process (see sample()).
    """
    pv_by_name = {entry["name"]: entry["pv"] for entry in pv_defs}
    values = _caget_many(caget_path, pv_by_name, timeout_sec)

    entries_by_name = {entry["name"]: entry for entry in pv_defs}
    online = {}
    offline = []
    for name, entry in entries_by_name.items():
        if values.get(name) is not None:
            online[name] = entry
        else:
            offline.append(entry)

    return online, offline


def format_discovery_report(online, offline):
    lines = ["{} of {} PVs online".format(len(online), len(online) + len(offline)), ""]
    for name in sorted(online):
        lines.append("  [ONLINE ] {:<40} {}".format(name, online[name]["pv"]))
    for entry in sorted(offline, key=lambda e: e["name"]):
        lines.append("  [OFFLINE] {:<40} {}".format(entry["name"], entry["pv"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def sample(online_pv_defs, timeout_sec, caget_path=DEFAULT_CAGET_PATH):
    """
    Read every PV that was online at discovery time - a fresh `caget` call
    per PV each cycle (no persistent connection/subscription to reuse,
    unlike pyepics' cached CA monitors - see the module docstring for why).

    Returns (values: {name: value or OFFLINE_MARKER}, currently_offline:
    [name]) - currently_offline lists every PV that didn't respond this
    cycle, whether it just dropped or has been down since a prior one.
    """
    pv_by_name = {name: entry["pv"] for name, entry in online_pv_defs.items()}
    raw_values = _caget_many(caget_path, pv_by_name, timeout_sec)

    values = {}
    currently_offline = []
    for name in online_pv_defs:
        value = raw_values.get(name)
        if value is not None:
            values[name] = value
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
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
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


def read_logged_pv_names(csv_path):
    """The list of PV names (write_header's own `name` values, not raw PV
    strings) that a previously-logged CSV actually tracked - read back
    from its header row, so a GUI can offer "load this run's PV
    selection" from any past CSV rather than only ever remembering the
    single most recent dialog session.

    Skips '#'-prefixed audit-trail comment lines (see write_header) and
    blank lines to find the real header - the first "Date, name1, name2,
    ..." line. Tolerant of write_header's trailing ", " after the last
    column (splitting on "," and dropping empty/whitespace-only pieces
    handles it without a special case). Returns [] for a file that's
    missing, empty, or doesn't start with the expected "Date" column -
    better to come back with nothing to select than guess at a format
    this wasn't actually built for.
    """
    try:
        with open(csv_path) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = [p.strip() for p in line.rstrip("\n").split(",")]
                parts = [p for p in parts if p]
                if parts and parts[0] == "Date":
                    return parts[1:]
                return []
    except OSError:
        return []
    return []


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
    online, offline = discover_pvs(cfg["pvs"], cfg["settings"]["connect_timeout_sec"], cfg["settings"]["caget_path"])
    print(format_discovery_report(online, offline))
    return 0


_stop_requested = False


def _handle_sigterm(signum, frame):
    # Set a flag rather than exiting the process directly - cmd_start's
    # loop checks this so it can write a clean STOPPED status (see
    # --status-file) before actually exiting, the same "cooperative
    # cancellation" pattern data_integrity/checksum_worker.py uses for its
    # own detached jobs. Without this, `systemctl --user stop` on a
    # persistent PV-logging job would just kill it mid-cycle with no
    # record of a clean shutdown.
    global _stop_requested
    _stop_requested = True


def cmd_start(args):
    cfg = load_config(args.config)
    if args.interval is not None:
        cfg["settings"]["log_interval_sec"] = args.interval
    caget_path = cfg["settings"]["caget_path"]
    connect_timeout_sec = cfg["settings"]["connect_timeout_sec"]
    status_file = args.status_file

    signal.signal(signal.SIGTERM, _handle_sigterm)

    print("Discovering PVs (timeout {}s)...".format(connect_timeout_sec))
    online, offline = discover_pvs(cfg["pvs"], connect_timeout_sec, caget_path)
    print(format_discovery_report(online, offline))

    if not online:
        print("No PVs online - nothing to log.", file=sys.stderr)
        if status_file:
            rj.atomic_write_json(status_file, {
                "state": "FAILED",
                "error_message": "No PVs online at discovery time",
                "finished_at": time.time(),
            })
        return 1

    names = sorted(online)
    write_header(args.outfile, names)
    offline_at_discovery = sorted(entry["name"] for entry in offline)
    if offline:
        skipped_path = write_skipped_report(args.outfile, offline)
        print("Offline-at-start PVs recorded in: {}".format(skipped_path))

    # Every PV this job was asked to track, whether or not it ever
    # actually connected - lets a status-file reader (pv_logger_gui.py's
    # expandable per-beamline PV list) show a PV that's been offline
    # since before logging even started, not just one that dropped
    # mid-run. `names`/`online` alone can't do this: sample() only ever
    # re-checks PVs that connected at discovery time (see its own
    # docstring), so a PV offline from the start would otherwise never
    # appear in `currently_offline` at all - confirmed directly, a run
    # with 4 already-offline PVs showed "13 of 17 online" but the
    # expandable list only ever listed the 13, all green, no way to see
    # which 4 were the problem.
    tracked = sorted(names + offline_at_discovery)

    if args.test_email:
        ok = send_drop_alert(cfg, [names[0]], args.outfile, dry_run=args.dry_run)
        return 0 if ok else 1

    started_at = time.time()

    def _write_status(state, currently_offline=(), error_message=None):
        if not status_file:
            return
        # currently_offline (from sample(), if any) only ever names PVs
        # that dropped AFTER connecting at discovery - union in the
        # PVs that were already offline at discovery (permanently, since
        # sample() never re-checks them) so the status file always
        # reflects every currently-offline PV, not just newly-dropped
        # ones.
        all_offline = sorted(set(offline_at_discovery) | set(currently_offline))
        payload = {
            "state": state,
            "outfile": args.outfile,
            "started_at": started_at,
            "updated_at": time.time(),
            "online_count": len(tracked) - len(all_offline),
            "total_count": len(tracked),
            "currently_offline": all_offline,
            # Every PV actually being tracked, whether online at discovery
            # or not - lets a GUI show the full online/offline breakdown
            # for a running job, not only whichever subset happened to be
            # reachable at the very start. Fixed for the job's lifetime,
            # same as `names`/`online` themselves.
            "tracked": tracked,
        }
        if error_message is not None:
            payload["error_message"] = error_message
        rj.atomic_write_json(status_file, payload)

    _write_status("RUNNING")

    interval = cfg["settings"]["log_interval_sec"]
    print("Logging every {}s to {}. Ctrl-C to stop.".format(interval, args.outfile))
    try:
        while not _stop_requested:
            now = time.time()
            values, currently_offline = sample(online, connect_timeout_sec, caget_path)
            write_row(args.outfile, names, values, now)
            dropped = process_drop_alerts(cfg, currently_offline, args.outfile, dry_run=args.dry_run)
            if dropped:
                print("Alert sent for offline PV(s): {}".format(", ".join(dropped)))
            _write_status("RUNNING", currently_offline)

            # Sleep in small chunks so a SIGTERM (a remote `systemctl --user
            # stop`) is noticed promptly rather than waiting out however
            # much of log_interval_sec is left.
            slept = 0.0
            while slept < interval and not _stop_requested:
                chunk = min(0.5, interval - slept)
                time.sleep(chunk)
                slept += chunk
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        # Broad on purpose: as a detached remote job, nothing else is
        # watching this process - an uncaught exception here would
        # otherwise crash silently, leaving the status file stuck at a
        # stale "RUNNING" forever (the GUI has no way to tell a crashed
        # job from a slow one) - the same stuck-status class of bug this
        # project already hit and fixed once for checksum jobs.
        print("PV logging crashed: {}".format(e), file=sys.stderr)
        _write_status("FAILED", error_message=str(e)[:2000])
        return 1

    _write_status("STOPPED")
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
    start_p.add_argument("--status-file", default=None,
                          help="Write live JSON status here (state/online-count/currently-offline) - "
                               "used when this runs as a detached remote job so a GUI can poll it")
    start_p.set_defaults(func=cmd_start)

    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
