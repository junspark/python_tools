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

# Largest top-level subdirectories of a target, with each one's most
# recent modification time - "what's actually taking up the space, and
# is it stale enough to delete?" Walks the whole tree (same cost as `du`
# itself), so this is a deliberate, on-demand command, not something
# check/monitor ever run automatically.
python disk_monitor.py top-folders --target s1c
python disk_monitor.py top-folders --path /any/directory --top 10
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
- **Edit recipients...** — opens a dialog listing alert email addresses one
  per line (still tolerates comma-separated addresses pasted into a single
  line).
- **Send test email** — sends (or prints, if `recipients` is empty) a test
  alert for the selected row, or the first target if none selected.
- **Top folders...** — for the selected row's target (or the first target
  if none selected), scans in the background and shows its top 5 largest
  immediate subdirectories, each with its size and most recent
  modification time anywhere underneath it (via `du --time` - see
  `top_level_breakdown()` in `disk_monitor.py`). Meant to answer "what's
  actually filling this up, and is any of it old enough to be safe to
  delete" - a single overall used/free percentage can't tell you that.
  This walks the target's entire tree (same cost as the CLI's
  `top-folders`), so on a multi-TB mount it can take a while; the scan
  runs off the GUI thread so the rest of the panel keeps working while
  you wait, and the dialog can be closed at any time. Runs with lowered
  CPU/I/O priority (`ionice -c3`/`nice -n 19`) when those tools are
  available, so a scan of a multi-TB mount doesn't starve the panel's own
  regular refresh - or anything else hitting the same NFS server - while
  it works; falls back to a plain `du` if they aren't installed.
  Dereferences only the target path itself if it's a symlink (not every
  symlink found while walking it), so a monitored target that's itself a
  symlink (a common setup here) is scanned correctly instead of reporting
  "No subdirectories found."
- **Recent activity** column — filled in automatically in the background
  shortly after the GUI starts (and refreshed for whichever target you
  just ran **Top folders...** on manually), by scanning every configured
  target's top-level folders sequentially, one `du` at a time, off the GUI
  thread - the same scan **Top folders...** runs on demand, just automatic
  and covering every target instead of one at a time. Shows the single
  most recently touched top-level folder and how long ago
  (`name (Nh ago)`); hover the cell for a tooltip breaking out the top 3
  largest and top 3 most recently edited folders separately - size and
  recency are independent signals (a folder can be huge but untouched for
  months, or tiny but being written to right now), so neither ranking
  alone tells the whole story. Shows `Scanning...` until that target's
  scan completes; on a target with a lot of data this is the same cost as
  **Top folders...** itself, but doesn't block the rest of the panel while
  it runs.
- **Disk monitor: ...** — a best-effort, read-only health check of the
  unattended `check` cron job, refreshed every cycle, color-coded green/red
  the same way the table's Status column is:
  - `Disk monitor: OK` (green) — `crond`/`cron` service is active and a
    crontab entry referencing `disk_monitor.py` exists.
  - `Disk monitor: SERVICE DOWN` (red) — `crond`/`cron` isn't running on
    this host at all.
  - `Disk monitor: not scheduled` (red) — the service is up but no
    crontab entry references this script (e.g. it was removed, or you're
    running as a different user than the one with the crontab).
  - `Disk monitor: unknown` (gray) — couldn't determine either (e.g. no
    `systemctl`/`crontab` on this host); not a reliable signal either way.

  This only checks that cron *should* run the job, not that it's succeeding.
  Pair it with the monitoring-gap warning below for that.
- **Monitoring gap warning** — on every refresh, the status bar checks how
  long it's been since the last sample recorded for each target *before*
  this cycle's own write. If that gap exceeds 2x `check_interval_sec`, it's
  shown as `⚠ monitoring gap detected: <name> (<N> min)`. This is most
  useful right after (re)opening the GUI: a large gap there means nothing —
  neither cron nor a running GUI — was actually recording samples while you
  were away, even if `Disk monitor: OK` says the job is scheduled.
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
