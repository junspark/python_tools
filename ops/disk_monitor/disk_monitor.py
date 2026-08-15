#!/usr/bin/env python3
"""
Disk-space monitor: usage, fill rate, and email alerts.

Watches a configurable list of filesystem paths (see disk_monitor_config.json),
tracks how fast each one is filling up, and emails a recipient list before a
target crosses its threshold (default 95%).

This module is dependency-light: everything below uses only the standard
library, so `check`/`monitor` work with a bare Python 3 install. The PyQt5
GUI (disk_monitor_gui.py) imports this module rather than duplicating logic.

Subcommands
-----------
check     One pass over all targets; sends alert emails as needed. This is
          what you'd put in cron.
monitor   Same check, looped on --interval, printing a color-coded table.

Usage examples
--------------
  python disk_monitor.py check
  python disk_monitor.py check --dry-run
  python disk_monitor.py check --test-email
  python disk_monitor.py monitor --interval 60
  */15 * * * * /usr/bin/python3 /path/to/disk_monitor.py check   # crontab
"""

import argparse
import json
import os
import shutil
import smtplib
import socket
import sys
import time
from email.mime.text import MIMEText

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "disk_monitor_config.json")
DEFAULT_HISTORY_PATH = os.path.join(SCRIPT_DIR, "disk_history.jsonl")
DEFAULT_STATE_PATH = os.path.join(SCRIPT_DIR, "disk_alert_state.json")

GB = 1024 ** 3

_ANSI = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "reset": "\033[0m"}

_DEFAULT_SETTINGS = {
    "recipients": [],
    "sender": "disk_monitor@{host}".format(host=socket.gethostname()),
    "smtp_host": "apsmail.aps.anl.gov",
    "smtp_port": 25,
    "check_interval_sec": 60,
    "rate_window_min": 10,
    "alert_cooldown_min": 60,
    "history_retention_hours": 24,
    "history_file": DEFAULT_HISTORY_PATH,
    "state_file": DEFAULT_STATE_PATH,
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path=DEFAULT_CONFIG_PATH):
    """Load the JSON config and fill in any missing settings with defaults."""
    with open(path) as f:
        cfg = json.load(f)

    settings = dict(_DEFAULT_SETTINGS)
    settings.update(cfg.get("settings", {}))
    cfg["settings"] = settings

    for target in cfg.get("targets", []):
        target.setdefault("threshold_pct", 95)
        target.setdefault("warn_pct", 85)

    return cfg


def save_config(cfg, path=DEFAULT_CONFIG_PATH):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Usage sampling
# ---------------------------------------------------------------------------

def sample_usage(path):
    """Return (total, used, free, percent) bytes/pct for the filesystem at path."""
    total, used, free = shutil.disk_usage(path)
    percent = (used / total * 100.0) if total else 0.0
    return total, used, free, percent


# ---------------------------------------------------------------------------
# History + rate
# ---------------------------------------------------------------------------

def _read_history(history_file):
    if not os.path.exists(history_file):
        return []
    entries = []
    with open(history_file) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def record_history(history_file, name, timestamp, used_bytes, retention_hours):
    """Append a sample for `name` and prune entries older than retention_hours."""
    entries = _read_history(history_file)
    entries.append({"name": name, "ts": timestamp, "used": used_bytes})

    cutoff = timestamp - retention_hours * 3600
    entries = [e for e in entries if e["ts"] >= cutoff]

    with open(history_file, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    return [e for e in entries if e["name"] == name]


def compute_rate(history_entries, now, window_min):
    """
    Running-average bytes/day growth rate, linear-fit over just the last
    window_min minutes of history (default 15) so a sudden burst of writes
    is reflected quickly instead of being smoothed out by older samples.
    """
    cutoff = now - window_min * 60
    points = sorted((e["ts"], e["used"]) for e in history_entries if e["ts"] >= cutoff)
    if len(points) < 2:
        return 0.0

    n = len(points)
    mean_t = sum(t for t, _ in points) / n
    mean_u = sum(u for _, u in points) / n
    num = sum((t - mean_t) * (u - mean_u) for t, u in points)
    den = sum((t - mean_t) ** 2 for t, _ in points)
    if den == 0:
        return 0.0

    return (num / den) * 86400


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def _status_level(percent, warn_pct, threshold_pct):
    if percent >= threshold_pct:
        return "alert"
    if percent >= warn_pct:
        return "warn"
    return "ok"


def check_targets(cfg, now=None):
    """Sample every configured target, update history, return status dicts."""
    if now is None:
        now = time.time()

    settings = cfg["settings"]
    results = []

    for target in cfg["targets"]:
        name, path = target["name"], target["path"]
        try:
            total, used, free, percent = sample_usage(path)
        except OSError as exc:
            results.append({
                "name": name, "path": path, "error": str(exc),
                "level": "error",
            })
            continue

        history = record_history(
            settings["history_file"], name, now, used,
            settings["history_retention_hours"],
        )
        rate_bytes_per_day = compute_rate(history, now, settings["rate_window_min"])
        eta_days = None
        if rate_bytes_per_day > 0:
            eta_days = free / rate_bytes_per_day

        level = _status_level(percent, target["warn_pct"], target["threshold_pct"])

        results.append({
            "name": name,
            "path": path,
            "total": total,
            "used": used,
            "free": free,
            "percent": percent,
            "rate_bytes_per_day": rate_bytes_per_day,
            "eta_days": eta_days,
            "threshold_pct": target["threshold_pct"],
            "warn_pct": target["warn_pct"],
            "level": level,
            "ts": now,
        })

    return results


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


def _format_alert_body(status, all_statuses=None):
    lines = [
        "Disk usage alert on {}".format(socket.gethostname()),
        "",
        "Target:    {}".format(status["name"]),
        "Path:      {}".format(status["path"]),
        "Used:      {:.1f}% ({:.1f} GB free of {:.1f} GB)".format(
            status["percent"], status["free"] / GB, status["total"] / GB),
        "Threshold: {}%".format(status["threshold_pct"]),
    ]
    if status["eta_days"] is not None:
        lines.append("Fill rate: {:.2f} GB/hr (full in ~{:.1f} days at this rate)".format(
            status["rate_bytes_per_day"] / 24 / GB, status["eta_days"]))

    if all_statuses:
        lines.append("")
        lines.append("All monitored paths:")
        lines.append(format_table(all_statuses, color=False))

    return "\n".join(lines)


def send_alert_email(cfg, status, all_statuses=None, dry_run=False):
    settings = cfg["settings"]
    subject = "DISK ALERT: {} at {:.1f}% on {}".format(
        status["name"], status["percent"], socket.gethostname())
    body = _format_alert_body(status, all_statuses)

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
        print("Failed to send alert email for {}: {}".format(status["name"], exc), file=sys.stderr)
        return False

    return True


def process_alerts(cfg, statuses, dry_run=False, force=False):
    """Send alert emails for targets in 'alert' level, respecting cooldown."""
    settings = cfg["settings"]
    state = _load_state(settings["state_file"])
    cooldown_sec = settings["alert_cooldown_min"] * 60
    now = time.time()
    sent = []

    for status in statuses:
        if status.get("level") != "alert":
            continue

        last = state.get(status["name"], 0)
        if not force and (now - last) < cooldown_sec:
            continue

        if send_alert_email(cfg, status, all_statuses=statuses, dry_run=dry_run):
            sent.append(status["name"])
            if not dry_run:
                state[status["name"]] = now

    if sent and not dry_run:
        _save_state(settings["state_file"], state)

    return sent


# ---------------------------------------------------------------------------
# Terminal display (used by `monitor`)
# ---------------------------------------------------------------------------

def _color_for_level(level):
    return {"ok": "green", "warn": "yellow", "alert": "red"}.get(level, "red")


def format_table(statuses, color=True):
    header = "{:<20} {:<30} {:>8} {:>10} {:>12} {:>12}".format(
        "NAME", "PATH", "USED%", "FREE(GB)", "RATE(GB/hr)", "ETA(days)")
    lines = [header, "-" * len(header)]

    for s in statuses:
        if s.get("level") == "error":
            lines.append("{:<20} {:<30} ERROR: {}".format(s["name"], s["path"], s["error"]))
            continue

        eta = "{:.1f}".format(s["eta_days"]) if s["eta_days"] is not None else "-"
        row = "{:<20} {:<30} {:>7.1f}% {:>10.1f} {:>12.2f} {:>12}".format(
            s["name"], s["path"], s["percent"], s["free"] / GB,
            s["rate_bytes_per_day"] / 24 / GB, eta)
        if s["level"] == "alert":
            row += "   <== ALERT (over {}% threshold)".format(s["threshold_pct"])
        if color:
            row = _ANSI[_color_for_level(s["level"])] + row + _ANSI["reset"]
        lines.append(row)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_check(args):
    cfg = load_config(args.config)
    statuses = check_targets(cfg)
    print(format_table(statuses))

    if args.test_email:
        target_statuses = [s for s in statuses if s.get("level") != "error"]
        if not target_statuses:
            print("No valid targets to send a test email for.", file=sys.stderr)
            return 1
        test_status = dict(target_statuses[0])
        test_status["level"] = "alert"
        ok = send_alert_email(cfg, test_status, all_statuses=statuses, dry_run=args.dry_run)
        return 0 if ok else 1

    sent = process_alerts(cfg, statuses, dry_run=args.dry_run)
    if sent:
        print("Alert email sent for: {}".format(", ".join(sent)))
    return 0


def cmd_monitor(args):
    cfg = load_config(args.config)
    try:
        while True:
            os.system("clear" if os.name == "posix" else "cls")
            statuses = check_targets(cfg)
            print(format_table(statuses))
            sent = process_alerts(cfg, statuses, dry_run=args.dry_run)
            if sent:
                print("\nAlert email sent for: {}".format(", ".join(sent)))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Monitor disk usage/fill-rate and email alerts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to config JSON")
    common.add_argument("--dry-run", action="store_true", help="Print alert emails instead of sending")

    check_p = subparsers.add_parser("check", parents=[common], help="Run one check-and-alert pass")
    check_p.add_argument("--test-email", action="store_true",
                          help="Force-send a test alert for the first target, ignoring threshold/cooldown")
    check_p.set_defaults(func=cmd_check)

    monitor_p = subparsers.add_parser("monitor", parents=[common], help="Loop, printing a status table")
    monitor_p.add_argument("--interval", type=float, default=60, help="Seconds between checks")
    monitor_p.set_defaults(func=cmd_monitor)

    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
