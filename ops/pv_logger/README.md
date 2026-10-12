# PV Logger

## Overview

A portable replacement for the old `exp_tracking.py` (Python 2, SPEC/APSpy,
hardcoded per-experiment motor/PV list requiring manual comment/uncomment).
Give it one **master list** of every PV ever used across setups; at the
start of each experiment it probes which ones are actually online *right
now* and logs only those — no editing PV definitions per run. If a PV that
was online drops out mid-run, that's logged as `OFFLINE` and (optionally)
emailed as an alert.

Runs as a **persistent, detached job per beamline** (`s1` and `s20` each
have their own master list, host, and job), launched from the GUI but
surviving it being closed — the same architecture `ops/data_integrity`'s
Verify MD5 jobs use. No `pyepics` dependency: PVs are read by shelling out
to the `caget` CLI (facility-wide EPICS Base install) via a bounded thread
pool, one process per PV, since neither beamline host this actually runs on
has a working `pyepics` install.

| File | Purpose |
|---|---|
| `pv_logger.py` | stdlib-only core module + CLI (`list-pvs`, `start`) |
| `pv_logger_gui.py` | PyQt5 GUI; imports `pv_logger.py`, no separate logic |
| `pv_device_categories.py` | Shared, stdlib-only device-category data (`DEVICE_CATEGORIES`) — used by both the GUI's Pick PVs checklist and `pv_logger.py`'s CSV column ordering |
| `pv_master_list_s1.json` / `pv_master_list_s20.json` | Per-beamline master PV list (name/PV/group) + settings |
| `pv_alert_state.json` | Auto-generated: last-alert time per PV (cooldown) |
| `pv_logger_selection_prefs.json` | Auto-generated: last PV selection per beamline (dialog convenience, gitignored) |

## Setup

Needs PyQt5 (GUI only) in the shared `ops` conda environment
(`../../environment.yml`):

```bash
conda env create -f ../../environment.yml   # or: conda env update -f ../../environment.yml
conda activate ops
```

`caget` itself needs no setup — `settings.caget_path` points at a
facility-wide shared NFS mount
(`/APSshare/epics/base-7.0.10/bin/rhel9-x86_64/caget`), identically present
on every beamline host, no per-account activation required.

## Persistent remote jobs

`pv_logger_gui.py`'s **Start new experiment...** doesn't run discovery or
logging on the GUI's own host — it launches `pv_logger.py start` as a
detached `systemd --user` job on the beamline's own designated host, via
SSH (shared `remote_job.py` primitives, same pattern as Verify MD5):

| Beamline | Host | User |
|---|---|---|
| `s1` | `egressy` | `s1iduser` |
| `s20` | `zion` | `s20iduser` |

This routing (`settings.remote_job` in each master list) is about EPICS
Channel Access reachability, not compute capacity — deliberately different
from `data_integrity`'s checksum-job routing, which runs both beamlines'
jobs on `zion`.

Once launched, the job keeps running detached even if the GUI is closed or
the launching machine reboots — `pv_logger_gui.py` reattaches to it by
polling its status file (`<remote_base>/status/<beamline>.json`, a plain
local read over the shared filesystem, no SSH needed), the same
reattachment mechanism Verify MD5 uses. Only one active logger per beamline
is enforced by an atomic `mkdir`-based lock, checked before launch.
**Stop** requests a clean `systemctl --user stop`, which the job's own
SIGTERM handler turns into a final `STOPPED` status write rather than a
bare kill.

## Master PV list

`pv_master_list_s1.json` / `pv_master_list_s20.json`:

```json
{
  "settings": {
    "log_interval_sec": 5,
    "connect_timeout_sec": 2.0,
    "caget_path": "/APSshare/epics/base-7.0.10/bin/rhel9-x86_64/caget",
    "recipients": ["you@aps.anl.gov"],
    "sender": "pv_logger@your-host.aps.anl.gov",
    "smtp_host": "apsmail.aps.anl.gov",
    "smtp_port": 25,
    "alert_cooldown_min": 60,
    "remote_job": {
      "host": "zion",
      "user": "s20iduser",
      "remote_base": "/home/beams/S20IDUSER/pv_logger"
    }
  },
  "pvs": [
    { "name": "Iring", "pv": "S:SRcurrentAI", "group": "Storage Ring" },
    { "name": "hydraZE", "pv": "1idc:m7.RBV", "group": "D3E-Hydra motion" }
  ]
}
```

| Setting | Default | Meaning |
|---|---|---|
| `log_interval_sec` | `5` | Seconds between samples once `start` is logging |
| `connect_timeout_sec` | `2.0` | `caget` timeout per PV — PVs are probed in parallel via a bounded thread pool, so total discovery/sample time is bounded by this regardless of how many PVs end up offline, not multiplied by offline count |
| `caget_path` | facility-wide `/APSshare` install | Only needs overriding for a host without that exact mount |
| `recipients` | `[]` | Alert email addresses. Empty = alerts print to console instead of sending |
| `sender` / `smtp_host` / `smtp_port` | — / `apsmail.aps.anl.gov` / `25` | Same relay pattern as `ops/disk_monitor` |
| `alert_cooldown_min` | `60` | Minimum time between repeat alert emails for the same PV while it stays offline |
| `remote_job` | — | `{host, user, remote_base}` for this beamline's persistent job (see above). Missing = Start new experiment refuses to launch |

To add a PV: append `{"name": ..., "pv": ..., "group": ...}` to `pvs`. To
retire one: delete its entry, or just leave it — an unreachable PV is
silently skipped at discovery, no need to comment it out.

**`"name"` must be unique across the entire file, not just within a
group.** `discover_pvs`, `sample`, and the CSV header all key PVs by
`"name"` in a plain dict — two entries sharing a name (even across
unrelated groups) silently collapse into one, with no error and no
warning, dropping every duplicate but the last one seen. This bit s20
for real: eight different detector groups (BSE1, BSE2, the old "D3
Detector", D4-1, D4-2, GH2, PG6, PITEC1) all reused identical generic
areaDetector attribute names like `DetGain`/`DetModel`/`DetBinX` for
their own cameras — fine as long as only one such group was ever
selected at a time, but selecting several together (confirmed directly:
a 421-PV pick) silently logged/checked only 254 of them, no visible
sign anything was missing. Fixed (2026-10-01) by prefixing every one of
those generic names with its own group tag (`DetGain` → `BSE1 DetGain`,
etc.) and splitting "D3 Detector" into its three actually-distinct
physical cameras (`QMPX3 Detector`/`SP1 Detector`/`Lambda Detector`) plus
a separate `D3 Detector motion` group for their shared hutch stage. When
adding a new device, especially a new camera/detector sharing a common
driver's standard PV suffixes with an existing one, double check its
`"name"` values don't collide with anything already in the file — not
just within its own group.

### Device categories

The Start-new-experiment checklist groups devices under category headers
(`DEVICE_CATEGORIES`, in the shared `pv_device_categories.py` module) —
e.g. separate "B/C/D/E Lens Stacks", "B/C/E Slits"/"White Beam Slits", and
"B/C/E Hutch Ion Chambers" groups, mirroring the hutch/position a device
actually belongs to rather than one generic "Slits" or "Ion Chamber"
bucket. A device not mapped to any category falls into "Other" at the end.
To add a new device group, give its PVs a `"group"` value in the master
list and (optionally) add that name to the relevant category in
`DEVICE_CATEGORIES` — an unmapped group still shows up fine under "Other",
categorization is a display convenience, not a requirement.
`DEVICE_CATEGORIES` is shared across both beamlines' master lists — before
removing or renaming an entry, check both master lists for real members,
not just one.

`pv_device_categories.py` has no imports beyond the standard library (it
originally lived inside `pv_logger_gui.py`, PyQt5 and all, and was
extracted so the headless CLI/systemd logger could reuse the same category
data too — see below — without gaining a GUI dependency).

### CSV column ordering

`start` lays a freshly-created outfile's columns out in a fixed scientific
order rather than `pv_master_list`'s own group order: **Storage Ring →
Monochromators → Slits & Ion Chambers → Sample Stack → Detectors → Sample
Environments**, with anything not covered by one of those buckets (e.g.
lab equipment, shutters, misc software signals) trailing at the end. This
is `CSV_CATEGORY_ORDER` in `pv_logger.py`, a further grouping of
`pv_device_categories.py`'s finer-grained categories into those six
buckets. The sort is stable, so PVs within the same device/group keep
their existing relative order — only whole category *blocks* move.

This only applies the first time an outfile is created — `start` freezes a
resumed outfile's columns to whatever header it already has (see below),
so re-ordering `CSV_CATEGORY_ORDER` or a PV's `"group"` never shifts an
already-running experiment's columns underneath it. To pick up a reorder,
Stop logging and Start again with a new outfile.

Where a physical device is naturally numbered (e.g. a lens stack with its
own motor per axis), give each unit its own `"group"` like `"C Lens Stack
1"` rather than lumping every unit under one generic device — this is what
lets the checklist show/select one stack at a time instead of all-or-
nothing for a whole hutch's optics. Not every device has this structure:
where the hardware itself has no natural numbering (e.g. s1's B hutch has
five distinct optics — `L1`, `L2`, `RL`, `CRL1`, `CRL2` — with different
axis sets and no shared "stack N" scheme), each unit keeps its own short
name as its `"group"` instead of an invented number.

Within a device group, PVs are ordered by `_pv_sort_key` rather than
raw alphabetical: a name ending in a motion-axis code sorts translation
axes before rotation axes (`X`, `Y`, `Z`, then `RX`, `RY`, `RZ`) — plain
alphabetical order would put every `RX`/`RY`/`RZ` first, since `R` sorts
before `X` in ASCII. Applies to both naming styles in use (`"C Lens1 X"`
and `"D_Lens1X"`). Anything else falls back to plain alphabetical, exactly
as before this existed.

## CLI usage

```bash
# Check what's online without logging anything - good before starting a run
python pv_logger.py list-pvs --config pv_master_list_s20.json

# Same, as machine-readable {"online": [...], "offline": [...]} JSON -
# what pv_logger_gui.py's "Check PVs..." button parses over SSH
python pv_logger.py list-pvs --config pv_master_list_s20.json --json

# Start logging - discovers online PVs, writes a CSV, alerts on drops, Ctrl-C to stop
python pv_logger.py start --config pv_master_list_s20.json --outfile ./logs/pokharel_jul26_run1.csv

# Override the sample interval, and print alert emails instead of sending
python pv_logger.py start --config pv_master_list_s20.json --outfile /tmp/t.csv --interval 2 --dry-run

# Verify the SMTP relay works end-to-end (force-sends one alert for the first online PV)
python pv_logger.py start --config pv_master_list_s20.json --outfile /tmp/t.csv --test-email

# As a detached remote job writes its own live status (used by pv_logger_gui.py, not usually passed by hand)
python pv_logger.py start --config pv_master_list_s20.json --outfile /tmp/t.csv --status-file /tmp/s20.json
```

`start` writes two things next to `--outfile`:
- The CSV itself, written with Python's `csv` module (proper quoting, not
  hand-joined text) — a `# Group` comment row naming each column's device
  group, then a `Date,name1,name2,...` header (skipped if the file already
  exists, so re-running `start` against the same `--outfile` resumes it),
  then one row per sample. A PV that's offline for a given sample —
  whether it never came online at discovery, or dropped mid-run — is
  written as the literal string `OFFLINE`. Proper quoting matters because
  several real PV/group names contain literal commas (e.g. `"GH1
  (Spinnaker, E-hutch)"`) — a hand-joined `", ".join(...)` format silently
  splits those into extra fields, shifting every later column out of
  alignment; `csv.writer` only quotes a field when it actually needs to,
  so a comma-free name still serializes exactly as before. Both the
  `# Group` row and the header are read back through `csv.reader`
  (`read_logged_pv_names`), still tolerant of the old pre-quoting format
  for historical files.
- `<outfile>.skipped.txt` — every master-list PV that wasn't online at
  discovery time, so it's on record per-experiment what wasn't hooked up.

`--status-file`, if given, gets a live JSON status written after every
sample cycle: `state` (`RUNNING`/`STOPPED`/`FAILED`), `online_count`,
`total_count`, `currently_offline` (every PV currently offline, whether it
dropped mid-run or was never online to begin with), `tracked` (every PV
this job was launched with), `outfile`, `started_at`/`updated_at`, and
`error_message` if `FAILED`. This is how `pv_logger_gui.py` shows live
status for a job without touching EPICS or the CSV file itself.

If the status-file's own filesystem fills up (confirmed directly: the
shared `/home/beams` mount backing `remote_job.remote_base`, separate
from wherever `--outfile` itself lives), writing a routine `RUNNING`
update raises `OSError: No space left on device` - caught by `cmd_start`'s
broad exception handler same as any other crash, which then tries to
record that as a `FAILED` status... which fails with the exact same
`ENOSPC` error, since it's the same disk. That second failure is now
caught too (logged to stderr as "Also failed to write FAILED status"
rather than propagating), so a disk-full crash produces one clear
traceback instead of a confusing cascade of two - but the underlying
status file is still left exactly where it was before the crash (a
RUNNING status that's now permanently stale), since there's no space to
write anything else to it. See "A stuck job that isn't really running"
below for how the GUI surfaces this.

### Viewing the log

The CSV is a plain wide table (time on rows, one column per PV) — open
directly in Excel, or in Python:

```python
import pandas as pd
df = pd.read_csv("run1.csv", comment="#", skipinitialspace=True)
df["Date"] = pd.to_datetime(df["Date"])
df.plot(x="Date", y=["hydraZE", "Furnace T1 (C)"])
```

`comment="#"` skips the leading `# Group` row (and any `# Devices`/`#
Timestamp` audit lines) so pandas reads the `Date,name1,name2,...` line as
the header rather than the comment row above it; `skipinitialspace=True`
is only needed for a historical file written before the `csv`-module
rewrite above (its trailing `", "` format left a stray space after each
comma).

with time on the X axis and any PVs on Y — useful for correlating a failed
scan against motor drift, beam drift, or a temperature excursion.

### Correlating with area-detector files

`correlate_ad_pvs.py` reads a logged CSV back and, for a set of
area-detector HDF5 files, interpolates the requested PVs to each
detector frame's acquisition time — area-detector acquisitions happen
asynchronously to the PV logger's own sampling cadence
(`log_interval_sec`), so a frame's timestamp essentially never lines up
exactly with a logged row.

```bash
# Find the per-frame timestamp attribute available in a real file first
python correlate_ad_pvs.py inspect --file scan_0001.h5

# One metadata CSV per input file, one row per frame
python correlate_ad_pvs.py per-frame --csv run1.csv --files 'scan_*.h5' \
    --pvs hydraZE geXE --groups "Eiger Acquisition Settings" \
    --pv-master-list pv_master_list_s1.json

# One combined CSV for the whole series, one row per file (frame-averaged)
python correlate_ad_pvs.py averaged --csv run1.csv --files 'scan_*.h5' \
    --pvs hydraZE geXE --out combined_pvs.csv \
    --pv-master-list pv_master_list_s1.json
```

- `--pvs` selects PVs by the same `name` used as the CSV column header;
  `--groups` selects every PV in a `pv_master_list_*.json` group (the
  same grouping the GUI's device-selection dialog filters on) — pass
  `--pv-master-list` when using `--groups`. Both can be combined.
- A requested PV that isn't actually a column in `--csv` (e.g. a group
  was added to the master list after this particular log was started)
  is skipped with a `WARNING` printed to stderr (or shown in the GUI's
  output panel), not treated as fatal — correlation still runs for
  every other requested PV. It's only an error if *none* of the
  requested PVs are present in the CSV.
- Numeric PVs are linearly interpolated between the two bracketing
  logged samples (constant-extrapolated past the first/last sample);
  non-numeric PVs (including ones that are `OFFLINE` at some samples)
  use the nearest logged sample instead.
- If a numeric PV's nearest real (online) sample is more than
  `--max-gap-sec` away from a frame's timestamp — whether the frame falls
  inside a mid-run offline gap, or the PV dropped permanently and never
  came back — that frame gets the literal string `OFFLINE` instead of an
  interpolated/extrapolated number, so a gap in logging never silently
  turns into a plausible-looking but made-up value. Default (when
  `--max-gap-sec` isn't given) is 3x the CSV's own median logging
  interval, so a single missed sample doesn't false-positive but an
  actual outage does.
- Per-frame timestamps are read from the HDF5 file itself where
  possible — the tool tries `misc/NDArrayTimeStamp` and a couple of
  other plausible attribute paths, and falls back to the file's mtime
  (with a warning) if none are found. **The right attribute path
  depends on how this beamline's areaDetector `layout.xml` is
  configured, which isn't recorded anywhere in this repo** — run
  `inspect` against one real file to confirm it, and override with
  `--timestamp-attr` if the default guess is wrong. If the embedded
  timestamp and the file's mtime disagree, the embedded per-frame value
  is used and a warning is printed — mtime only reflects when the file
  was closed, not when each frame in it was actually collected.

The GUI's "PV/AD Matcher" tab (`correlate_ad_pvs_gui.py`, also embedded in
`ops_gui.py`) wraps the same logic:

- Its "Beamline (for PV groups)" selector picks which
  `pv_master_list_*.json` the checked PV groups resolve against, and is
  otherwise independent of whichever CSV/AD files are chosen — so it's
  easy to leave it on the wrong beamline and end up with almost every
  requested PV silently skipped as "not logged in this CSV" (they *are*
  logged, just under the other beamline's group names). To catch this,
  the selector auto-switches whenever the chosen CSV path or the first
  added area-detector file path unambiguously names a beamline mount
  (`s1a`/`s1b`/`s1c`/`s20a`, or bare `s1`/`s20`) that disagrees with the
  current selection — a status-bar message says when this happens. It
  never guesses from an ambiguous path, so double-check the selector
  when your files live outside the usual `mnt/s1*`/`mnt/s20a` layout.
- "Mode" is two independent checkboxes, Per-frame and Averaged, not an
  either/or choice — check both to get both outputs from one run. Each
  file's frame timestamps and interpolated PV values are computed once
  and reused for whichever output(s) are checked, so checking both isn't
  twice the work of checking one.

## Alerting

Two kinds of emails, both via `settings.recipients`/`sender`/`smtp_host`/
`smtp_port` (same `apsmail.aps.anl.gov` relay pattern as `ops/disk_monitor`)
— empty `recipients` prints the would-be email to the console instead of
sending, same as `--dry-run`:

- **PV-drop alerts** — a PV that was online at discovery drops offline
  mid-run. Per-PV cooldown (`alert_cooldown_min`, default 60) so a flapping
  PV doesn't send an email every sample cycle.
- **Start-failure alerts** — the job fails before ever getting to the
  sampling loop: no PVs online at discovery, or a setup-time crash (e.g. an
  outfile the job's account can't write to — confirmed directly, a fresh
  experiment directory without the right group/ACL permissions for the
  service account raises exactly this). Unlike a mid-run PV drop, nothing
  is watching a status-file tree view for a job that never started
  logging, so this is a one-shot email rather than a polled/cooldown
  condition — sent once, whether or not `recipients` even gets a chance to
  see a RUNNING status first.

Every alert email ends with a footer identifying exactly which host,
account, and systemd unit sent it, and the exact command to stop it:

```
--
This alert was sent by a PV logger job running as s1iduser@egressy.xray.aps.anl.gov.
Beamline: s1 (systemd --user unit: pv-logger@s1.service)
To stop it: ssh s1iduser@egressy.xray.aps.anl.gov, then run: systemctl --user stop pv-logger@s1.service
```

This is derived entirely from `--status-file`'s own path (always
`<remote_base>/status/<beamline>.json` — see `pv_logger_status_path`) plus
`socket.gethostname()`/`getpass.getuser()` at send time, so it's always
accurate to wherever *that specific job* is actually running, not just a
generic "contact the PV logger maintainer" line. Confirmed directly this
is worth having: a stray, forgotten monitor script with no such note (not
even part of this tool — a one-off `nohup`'d `/tmp/monitor_*.sh` on a third
host) took real cross-host, cross-account digging to trace back to
anything actionable.

## GUI usage

```bash
python pv_logger_gui.py --config pv_master_list_s20.json
```

Deliberately **not** a live table of all ~500+ PVs — that's not something
you can usefully watch. Instead:

- A jobs tree shows **both s1 and s20 at once**, each row color-coded
  RUNNING (green) / STOPPED (gray) / FAILED (red), with the discovery
  summary (`N of M PVs online`) and output file in its Details column.
  Expand a beamline's row to see every individually-tracked PV's own
  online/offline state — not just a "currently offline" subset — so a PV
  that's been offline since before logging even started is just as
  visible as one that drops mid-run. A STOPPED/FAILED beamline's PVs are
  shown neutrally (not a false green/red) since only a running job's
  latest sample is trustworthy enough to assert either state.

  **A stuck job that isn't really running**: a `RUNNING` status is only as
  trustworthy as its last update is recent. A process that gets killed or
  crashes badly enough to bypass its own exception handler (confirmed
  directly: a disk-full error that broke the crash-recovery write too,
  see "status-file" above) never writes anything else - the status file
  just sits there saying `RUNNING` forever, looking identical to a
  genuinely healthy job, with nothing left for "Stop logging" to even act
  on (systemd's `--collect` already garbage-collected the dead unit, so
  stopping it fails with "Unit ... not loaded"). To catch this, a `RUNNING`
  row whose `updated_at` hasn't moved in more than 4x that beamline's
  `log_interval_sec` (floored at 30s, so a short configured interval
  doesn't false-positive on one merely-slow cycle) paints amber as
  **STALE?** instead of green, with "no update since ... (job may have
  crashed)" in its Details column. If you hit this: the job is already
  dead, nothing to Stop - either start a fresh run (which overwrites the
  stale status file with a live one as a side effect), or manually delete
  `<remote_base>/status/<beamline>.json` (and any leftover
  `<beamline>.json.tmp.<pid>` next to it - `atomic_write_json` cleans
  these up on a *future* failure now, but an already-orphaned one from
  before that fix needs a manual `rm`) to clear the display without
  starting new logging.
  Clicking any row in the tree (a beamline's own row, or one of its child
  PV rows) syncs the **Beamline** dropdown to match — the dropdown, not
  the tree selection, is what **Stop**/**Check PVs...**/**Edit
  recipients...** act on, so this keeps the two from silently disagreeing
  (e.g. clicking "s20" in the tree while the dropdown still says "s1",
  leaving **Stop** greyed out with no visible reason why).
- A FAILED or STOPPED transition also pops up a message box once, so a
  job that fails immediately (e.g. no PVs online at discovery) isn't
  missed.
- **Start new experiment...** opens a checklist of every device group in
  the master list. Click a group's checkbox to select/deselect all of its
  PVs at once, or click the disclosure triangle next to a group to expand
  it and check/uncheck individual PVs — the group checkbox shows a
  partial/tri-state mark when only some of its PVs are selected. The
  filter box at the top matches PV names and addresses too, not just
  device names, so e.g. typing a signal fragment finds it even if it
  never appears in any device name, and auto-expands any group it matched
  inside.

  Two ways to avoid re-building the same selection every time:
  - The dialog **remembers your last selection per beamline** automatically
    (`pv_logger_selection_prefs.json`) and pre-checks it the next time you
    open the dialog for that beamline. Because this happens automatically,
    a narrow test selection (e.g. checking just one device while testing
    the checklist UI) becomes the default for every subsequent launch
    until explicitly changed — if a launch seems to log far fewer PVs than
    expected, check what's actually selected before assuming a bug.
  - **Load selection from CSV...** reconstructs the *exact* PV selection
    used for any previous run, straight from that run's own logged CSV
    header row — useful for replicating an older experiment's setup rather
    than whatever was picked most recently.
- **Stop** requests a clean shutdown of the beamline's remote job (see
  "Persistent remote jobs" above) — the CSV/skipped-report already written
  stay on disk.
- **Check PVs...** probes the currently-selected beamline's *tracked* PV
  list — the same list its row in the jobs tree already shows (from the
  last run's status file or jobspec) — and recolors those same tree rows
  green/red, exactly like a RUNNING job's own live display. It's the GUI
  equivalent of `list-pvs --json` below, run on the beamline's own
  `remote_job` host, scoped down to just the tracked PVs rather than the
  whole (300+ PV) master list, since that's the list that actually
  matters here. A manual check's colors stick in the tree (surviving the
  normal poll cycle) until either a new job for that beamline goes
  RUNNING again, or another Check PVs is run. If the beamline has never
  been launched yet (nothing tracked to scope to), it falls back to
  checking the whole master list instead — still useful for confirming a
  PV's name/online-ness before a first **Start**. Doesn't start, stop, or
  otherwise touch any logging job — a purely point-in-time probe.
- **Edit recipients...** / **Font size** — same as `ops/disk_monitor`'s GUI.

This GUI is also available as a tab in `../ops_gui.py`, alongside
`ops/disk_monitor`'s GUI, if you'd rather run one combined window. The
underlying widget (`PVLoggerPanel` in `pv_logger_gui.py`) is shared between
the standalone window and that combined GUI - no separate code path.

## History

Originally `pyepics`-based and `s1`-only, built from `exp_tracking.py`'s
`spec.DefineMtr`/`mac.add_logging_PV` calls, `check_device_pvs.sh`'s device
groupings, and a SPEC macro's static `epics_get(...)` calls. Ported to the
`caget`-based, persistent-job, dual-beamline architecture described above
once neither `egressy` nor `zion` turned out to have a working `pyepics`
install or internet access to get one.
