# Disk Space Monitor

## Overview

Watches a configurable list of filesystem paths, tracks how fast each one is
filling up, and emails a recipient list before a path crosses its threshold
(default 95%).

| File | Purpose |
|---|---|
| `disk_monitor.py` | Stdlib-only core module + CLI (`check`, `monitor`) |
| `disk_monitor_gui.py` | PyQt5 GUI; imports `disk_monitor.py`, no separate logic |
| `disk_monitor_config.json` | Config: monitored paths, thresholds, email settings |
| `disk_history.jsonl` | Auto-generated: recent usage samples per target |
| `disk_alert_state.json` | Auto-generated: last-alert time per target (cooldown) |

`disk_monitor.py` only uses the standard library, so the `check`/`monitor`
CLI subcommands work with a bare Python 3 install — no setup needed. Only the
GUI requires an extra package.

---

## Setup

The GUI needs PyQt5. It's included in the shared `ops` conda environment
(`../../environment.yml`):

```bash
conda env create -f ../../environment.yml   # or: conda env update -f ../../environment.yml
conda activate ops
```

Or with pip only:

```bash
pip install PyQt5   # only needed for disk_monitor_gui.py
```

`check`/`monitor` send mail through the configured `smtp_host` (default
`apsmail.aps.anl.gov`, the APS outbound relay also used by
`APSpy_s1id/macros.py` in this repo). Most beamline hosts don't run their own
local MTA, so `localhost` will just time out — point `smtp_host` at a relay
that's actually reachable from wherever you run this. If it isn't reachable,
alert sends fail with a caught, logged error rather than crashing.

## Config file

`disk_monitor_config.json`:

```json
{
  "settings": {
    "recipients": ["you@aps.anl.gov"],
    "sender": "disk_monitor@your-host.aps.anl.gov",
    "smtp_host": "apsmail.aps.anl.gov",
    "smtp_port": 25,
    "check_interval_sec": 60,
    "rate_window_min": 10,
    "alert_cooldown_min": 60,
    "history_retention_hours": 24
  },
  "targets": [
    { "name": "home", "path": "/home/beams/PARKJS", "threshold_pct": 95, "warn_pct": 85 },
    { "name": "data", "path": "/net/s20data", "threshold_pct": 90, "warn_pct": 80 }
  ]
}
```

| Setting | Default | Meaning |
|---|---|---|
| `recipients` | `[]` | Email addresses to alert. Empty = alerts print to console instead of sending. |
| `sender` | `disk_monitor@<hostname>` | From address |
| `smtp_host` / `smtp_port` | `apsmail.aps.anl.gov` / `25` | Mail relay to send through — must be reachable from the host running this |
| `check_interval_sec` | `60` | How often `monitor` samples (and the GUI's refresh timer) |
| `rate_window_min` | `10` | Fill-rate (shown as GB/hr) is a **running average over this many trailing minutes**, not the full history — a sudden burst of writes shows up within one window instead of being smoothed out by older, quieter samples. Editable live from the GUI toolbar. |
| `alert_cooldown_min` | `60` | Minimum time between repeat alert emails for the same target while it stays over threshold |
| `history_retention_hours` | `24` | How long usage samples are kept in `disk_history.jsonl` |

Per-target `threshold_pct` (red/alert, triggers email) and `warn_pct`
(yellow, informational only) can be set individually per path.

To add or remove an alert email address, either use **Edit recipients...**
in the GUI toolbar, or edit the `recipients` list in
`disk_monitor_config.json` directly. If you hand-edit the file while the GUI
is open, restart the GUI afterward — it holds its own in-memory copy and
will overwrite your edit with stale data the next time it saves anything
(e.g. Add path, Rate avg).

---

## CLI usage

```bash
# One check-and-alert pass (what you'd put in cron)
python disk_monitor.py check

# Print what the alert email would say, without sending it
python disk_monitor.py check --dry-run

# Force-send one real alert for the first target, ignoring threshold/cooldown,
# to verify the SMTP relay actually works end to end
python disk_monitor.py check --test-email

# Continuous colored status table, refreshed every 30s, until Ctrl-C
python disk_monitor.py monitor --interval 30
```

### Recommended deployment: cron

`monitor` is for someone watching a terminal. For unattended monitoring, run
`check` on a schedule instead:

```cron
*/5 * * * * /usr/bin/python3 /path/to/ops/disk_monitor/disk_monitor.py check
```

---

## GUI usage

```bash
python disk_monitor_gui.py --config disk_monitor_config.json
```

- Table auto-refreshes on `check_interval_sec` and color-codes each row
  green/yellow/red by status level.
- **Add path...** — pick a directory, name it, and set warn/threshold %.
- **Remove selected** — drop the selected row(s) from monitoring.
- **Edit recipients...** — comma-separated list of alert email addresses.
- **Send test email** — sends (or prints, if `recipients` is empty) a test
  alert for the selected row, or the first target if none selected.
- **Cron: ...** — a best-effort, read-only health check of the unattended
  `check` cron job, refreshed every cycle:
  - `Cron: OK` — `crond`/`cron` service is active and a crontab entry
    referencing `disk_monitor.py` exists.
  - `Cron: SERVICE DOWN` — `crond`/`cron` isn't running on this host at all.
  - `Cron: not scheduled` — the service is up but no crontab entry
    references this script (e.g. it was removed, or you're running as a
    different user than the one with the crontab).
  - `Cron: unknown` — couldn't determine either (e.g. no `systemctl`/
    `crontab` on this host); not a reliable signal either way.

  This only checks that cron *should* run the job, not that it's succeeding.
  Pair it with the monitoring-gap warning below for that.
- **Monitoring gap warning** — on every refresh, the status bar checks how
  long it's been since the last sample recorded for each target *before*
  this cycle's own write. If that gap exceeds 2x `check_interval_sec`, it's
  shown as `⚠ monitoring gap detected: <name> (<N> min)`. This is most
  useful right after (re)opening the GUI: a large gap there means nothing —
  neither cron nor a running GUI — was actually recording samples while you
  were away, even if `Cron: OK` says the job is scheduled.
- **Rate avg (min)** — spinbox to change `rate_window_min` live.
- **Font size** — spinbox to resize the table text (display-only, not saved
  to config).
- Edits made in the GUI (targets, recipients, rate window) are saved back to
  the same config file the CLI reads, so `check`/`monitor` and the GUI
  always agree on what's monitored.

This GUI is also available as a tab in `../ops_gui.py`, alongside
`ops/pv_logger`'s GUI, if you'd rather run one combined window. The
underlying widget (`DiskMonitorPanel` in `disk_monitor_gui.py`) is shared
between the standalone window and that combined GUI - no separate code path.
