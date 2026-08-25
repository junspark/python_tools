# Data Integrity Monitor

Verifies that data staged locally at s1c/s20a has landed correctly on APS
Data Management (Sojourner). Provides a lightweight (file size/existence)
**Scan** and a slower, on-demand **Verify MD5** checksum check, plus
timestamped JSON records per experiment. Verify MD5 runs as a detached job
on `zion` that survives closing the GUI and is shared across everyone who
uses this tool - see "Persistent Checksum Jobs" below.

## Setup

**Important:** The GUI and the CLI's DM catalog queries need the APS Data
Management (DM) Python API, which is **not** part of the shared `ops`
conda environment. When running the CLI locally (no `remote_hosts`
configured for the relevant beamline), source the beamline's DM setup
first:

```bash
# Example for 1-ID (path may differ for your beamline)
source /dm/1id/etc/dm.setup.sh
conda activate dm-user
```

In practice, the GUI doesn't need this on the machine it runs on: DM
queries are routed over SSH to a beamline-appropriate host
(`settings.remote_hosts`/`setup_scripts`, e.g. `egressy` for s1,
`zion` for s20) that already has DM set up, so the GUI itself only needs
the shared `ops` environment:

```bash
conda activate ops
python dm_integrity_gui.py
```

`checksum_worker.py` (the detached MD5 job, see below) is stdlib-only -
it needs neither `ops` nor the DM environment on `zion`.

## Configuration

**`data_integrity_config.json`**:

```json
{
  "settings": {
    "station_name": "SOJOURNER",
    "records_dir": "/home/beams/PARKJS/ops_record",
    "remote_hosts": {"s1": "egressy", "s20": "zion"},
    "setup_scripts": {
      "s1": "~/bin/dm_setup_1id.sh dm",
      "s20": "~/bin/dm_setup_20ide.sh"
    },
    "local_root_templates": {
      "s1": "~/mnt/s1c/{expid}",
      "s20": "~/mnt/s20a/{expid}"
    },
    "local_bases": {"s1": "~/mnt/s1c", "s20": "~/mnt/s20a"},
    "experiments_per_beamline": 3,
    "checksum_hosts": {
      "s1":  {"host": "zion", "user": "s1iduser", "remote_base": "/home/beams/S1IDUSER/dm_record"},
      "s20": {"host": "zion", "user": "s20iduser", "remote_base": "/home/beams/S20IDUSER/dm_record"}
    },
    "checksum_cpu_budget": 0.20,
    "checksum_poll_interval_sec": 4,
    "upload_hosts": {
      "s1": "egressy",
      "s20": "redwood"
    }
  },
  "experiments": []
}
```

- **`station_name`**: DM storage system name (currently unused by the DM
  API calls themselves - kept for future use/labeling)
- **`records_dir`**: legacy, flat, per-launching-account records location
  from before records moved under each beamline's own account (see
  "Shared Records" below). Old records saved here remain visible in
  History; nothing new is written here.
- **`remote_hosts`** / **`setup_scripts`**: per-beamline (`s1`/`s20`)
  host and DM-setup-sourcing command for *DM catalog queries*
  (`get_upload_status`/`get_catalog_files`), reached over SSH. Both the
  GUI and the CLI route through these (`dm_integrity.remote_info_for_beamline`)
  - if a beamline is missing here, hardcoded defaults
  (`egressy`/`s1iduser` for s1, `zion`/`s20iduser` for s20) are used.
- **`local_root_templates`**: per-beamline convention path used when
  Scan/Verify MD5 needs a local root that discovery didn't already supply
  (e.g. a manually-added experiment).
- **`local_bases`**: per-beamline staging directories the GUI scans
  directly to build the experiment list (see "How Experiments Are Found"
  below). `~`-relative so the same config works whether the GUI is
  launched as `parkjs`, `S1IDUSER`, or `S20IDUSER` - all three resolve to
  the same real path.
- **`experiments_per_beamline`**: how many of each beamline's most-recent
  experiments to show (default 3, so 6 rows total for 2 beamlines).
- **`checksum_hosts`**: per-beamline `host`/`user`/`remote_base` for where
  Verify MD5 jobs actually *execute* and where their shared records/status
  live - see "Persistent Checksum Jobs". Distinct from `remote_hosts`
  above (that's for the fast DM catalog queries only).
- **`upload_hosts`**: per-beamline host for **Upload to DM** (`dm-upload
  --reprocess`, see "GUI Usage" below) - a third, distinct routing table
  from `remote_hosts` (DM catalog queries) and `checksum_hosts` (where
  Verify MD5 executes). Confirmed against each beamline's own
  end-of-experiment script (`dm_end_user_1id.sh`/`dm_end_user_20ide.sh`):
  s1's upload host happens to match its DM-query host (`egressy`), but
  s20's `dm-upload` must run from `redwood` specifically, not `zion`
  (where s20's DM-query/checksum jobs run) - a real, beamline-mandated
  SOP difference, not an oversight to reconcile away. If missing here,
  built-in defaults (`egressy` for s1, `redwood` for s20) are used.
- **`checksum_cpu_budget`**: aggregate CPU budget, as a fraction of one
  core (e.g. `0.20` = 20% of one core, `systemd`'s own `CPUQuota`
  convention), shared across *all* concurrently-running checksum jobs on
  `zion`, both beamlines combined.
- **`checksum_poll_interval_sec`**: how often the GUI re-reads a tracked
  checksum job's status file to update its progress display.
- **`experiments`**: two different kinds of entries share this list.
  Auto-discovered experiments (see "How Experiments Are Found") are
  cached here in-memory only, purely so Scan/Verify MD5 don't need to
  re-resolve a local root they already know - never written back to the
  file, and never carry a `"beamline"` key. Manually-added experiments
  (via the GUI's **Add EXPID...**, or a hand-edited entry for the CLI -
  see "CLI Usage") carry an explicit `"beamline"` key and ARE written
  back (`save_config()`), so they persist across restarts and reappear
  in the dashboard without being re-added.

## How Experiments Are Found

The GUI does **not** query DM/Sojourner to build its list. On startup it
scans `local_bases["s1"]` and `local_bases["s20"]` directly, keeping only
subdirectories whose name matches the real experiment-ID convention -
exactly `<piname>_<mon><yy>` (e.g. `park_may26`), not suffixed variants
like `brown_jul26_bc`. Recency is taken from the month/year encoded in the
name (not directory mtime, which can be skewed by unrelated backup
processes touching old folders), most-recent first, capped at
`experiments_per_beamline` per beamline. The table groups all of one
beamline's rows before the next beamline's.

This means: no SSH/DM round-trip just to open the tab, an experiment shows
up the moment there's local data even before anything's uploaded, and an
experiment whose name doesn't follow the convention won't be
auto-discovered (add it to the config's `experiments` list manually if
needed). Upload Status/Files start as `---` for every row - nothing is
checked against DM until you click **Scan** or **Verify MD5** on that row,
or a Verify MD5 job for it is already running/queued (see below).

An experiment auto-discovery doesn't surface - older than the most-recent
`experiments_per_beamline`, or named outside the `<piname>_<mon><yy>`
convention - can be added manually via **Add EXPID...** above the table.
It gets its own **Remove** button (auto-discovered rows don't - removing
one wouldn't stick, since the next startup just rediscovers it). Removing
an experiment only forgets it in this tool - no local files or Sojourner
data are touched.

## GUI Usage

```bash
python dm_integrity_gui.py          # standalone
python ../ops_gui.py                # combined with disk_monitor and pv_logger, as a tab
```

Each row has these actions:

- **Scan**: fast, size/existence-only comparison (no hashing). Queries DM
  upload status + file catalog over SSH, walks the local directory,
  classifies every file as `MATCH`/`SIZE_MISMATCH`/`LOCAL_ONLY`/`REMOTE_ONLY`
  (relocated files are reclassified out of these - see "Relocated Files"
  below), and saves a timestamped record. This is what fills in Upload
  Status/Files and colors the row.
- **Verify MD5 / Stop**: one button, not two. It reads **Verify MD5**
  normally and launches the slower checksum pass on top of Scan's
  matched files - see "Persistent Checksum Jobs" below. Once a job for
  that experiment is queued/running (locally tracked, or reattached from
  a job someone else launched) it relabels to **Stop**, which asks for
  confirmation and requests a clean shutdown of the remote job (progress
  isn't saved - a future run starts over). If a job hasn't reported
  progress in 15 minutes it's shown as **Stalled?** instead of
  "Verifying" - usually a crashed/killed remote process, but this
  beamline's ~30GB detector files can legitimately go this long between
  progress updates, so check before assuming it's dead. Stop on a
  stalled job offers to force-clear it rather than waiting on a shutdown
  handler that will never run for an already-dead process.
- **History**: opens a drill-down dialog for that experiment's saved
  Scan/Verify MD5 records - pick any past snapshot from a dropdown, see a
  per-category count table (good/missing/mismatched/relocated), the list
  of whole subdirectories that never landed on either side, and a
  filterable, file-by-file list of every problem in that snapshot. A
  compact "N recs" label next to the buttons shows at a glance whether
  history exists for a row without opening the dialog.
- **Upload to DM**: triggers `dm-upload --experiment=<name>
  --data-directory=<path> --reprocess` on the beamline's designated
  upload host (`settings.upload_hosts` - see Configuration; **not** the
  same host as DM catalog queries or Verify MD5) to push local files
  into Sojourner. Shows the exact command and asks for confirmation
  first - this writes into shared production infrastructure and can't
  be undone from here. dm-upload confirms the request was *accepted* and
  hands back an upload id; if that id parses cleanly (it normally does),
  the Upload Status/Files columns then update automatically every few
  seconds - `Uploading N% (X/Y uploaded)` while it runs, settling into
  `Done`/`Failed`/`Skipped`/`Aborted` once DM finishes - by querying that
  specific upload by id (`dm-get-upload-info`, via the same
  `ExperimentDaqApi` used elsewhere in this tool), not by
  re-running Scan/Verify MD5. If the id can't be parsed for some reason,
  it falls back to the old guidance: re-run Scan/Verify MD5 in a bit to
  see it reflected. Either way, a later Scan/Verify MD5 still overwrites
  the row with its own authoritative view.

Row coloring (`Files` column and beyond):
- **Green**: fully landed, upload complete, no problems - safe to delete
- **Red**: a real problem - `SIZE_MISMATCH`, `REMOTE_ONLY`, or
  `CHECKSUM_MISMATCH` present (checked ahead of green/yellow, so it can't
  be masked by an otherwise-good status; counts here are already
  post-relocation - see "Relocated Files" below)
- **Yellow**: `NOT_ON_SOJOURNER` - the expected state for a
  currently-running experiment, not necessarily a problem
- **Orange**: some other non-critical "bad" count (rare)
- **Blue**: a Verify MD5 job is queued/running for this row

Below that, a scrollable **Console** keeps a timestamped log of every
status/error message from this session (failures highlighted) - the
one-line status label above it can only ever show the latest message,
which made a long SSH failure or DM error unreadable before it was
overwritten by the next poll tick. **Clear** empties it; it isn't saved
anywhere.

Below the table, a per-beamline rollup line tallies whatever's already
been Scanned/Verified among the displayed rows, e.g.:

```
s1: 2/3 scanned - 1 on Sojourner, 1 not, 0 mismatch  |  s20: 1/3 scanned - 0 on Sojourner, 0 not, 1 mismatch
```

Rows not yet Scanned this session simply don't count yet (reflected in
the "N/M scanned" prefix) - nothing is auto-scanned to fill this in.

Font size (when run via `ops_gui.py`, one control drives all three tabs)
and window size persist across restarts, saved in `ops_gui_prefs.json`
next to `ops_gui.py`; window *position* deliberately does not persist,
since the same prefs file is read from whichever computer you log in
from, and a saved absolute position can land off-screen on a different
monitor layout.

## Persistent Checksum Jobs

Verify MD5 is not a `QThread` inside the GUI process - it launches
`checksum_worker.py` as a detached `systemd --user` service on `zion`,
under `s1iduser` (for s1c-based experiments) or `s20iduser` (for
s20a-based experiments), via `systemd-run --user --unit=checksum-verify@<expid>.service --collect`.
This means:

- **Survives closing the GUI.** `loginctl enable-linger` is enabled for
  both service accounts, so the job keeps running even with no active
  login. Reopening the GUI (yours or a colleague's) re-discovers a
  running job for that experiment from its status file - a plain local
  file read, no SSH - and shows live progress immediately.
- **Never double-launched.** An atomic `mkdir`-based lock
  (`<remote_base>/locks/checksum__<expid>`) is held while a launch is
  being set up, and the status file is checked for an existing
  QUEUED/RUNNING job first, so two GUI instances (or two users) clicking
  Verify MD5 on the same experiment at once only ever start one job. Scan
  has the same protection, under its own `scan__<expid>` lock (a Scan and
  a Verify MD5 for the same experiment don't conflict with each other).
- **CPU-limited, cooperatively.** `zion`'s `cpu` cgroup controller isn't
  delegated to user sessions, so `systemd`'s own `CPUQuota` is a no-op
  there. Instead, `checksum_worker.py` paces itself: it counts other
  currently-RUNNING checksum jobs (across **both** beamlines, by globbing
  both `checksum_status/` directories) and sleeps enough to keep its own
  share of `settings.checksum_cpu_budget` fair as that peer count changes.
  `--collect` on the systemd-run call additionally ensures a
  finished/failed job's transient unit is garbage-collected automatically,
  rather than lingering and blocking a future launch under the same
  deterministic unit name.

### Shared Records

Both Scan and Verify MD5 results are shared across whoever runs this GUI
- your own account, a colleague's, or directly as `s1iduser`/`s20iduser`
- not private to whoever happens to launch it. They live per-beamline,
under each service account's own home:

```
~s1iduser/dm_record/
  records/<year>/<expid>/<timestamp>.json   # Scan + Verify MD5 reports, s1 experiments
  checksum_status/<expid>.json              # in-progress/last-known Verify MD5 status
  checksum_status/<expid>.jobspec           # Verify MD5 job input (not read as history)
  locks/                                    # scan__<expid>, checksum__<expid>
~s20iduser/dm_record/
  ...                                       # same layout, s20 experiments
```

Both accounts' homes are world-readable, so any GUI instance can poll
status/history via a plain read regardless of who launched it; only
*writing* needs to happen as the owning account. Scan (which still runs
in-process, as whoever launched the GUI) writes its result there over
SSH (`save_record_remote`); `checksum_worker.py` writes locally since it
already runs as the right account.

`settings.records_dir` (default `/home/beams/PARKJS/ops_record`) is the
older, pre-this-feature, single-account location - still checked by
History for old records, but nothing new is saved there.

## CLI Usage

The GUI is the primary interface; the CLI below is a manual/scriptable
fallback and is not otherwise invoked by anything in this repo. It reads
`local_root` from the config's `experiments` list (add entries manually -
the GUI's discovery is in-memory only and isn't written back to the
file), and infers the beamline (for DM routing) either from an explicit
`"beamline"` key on that entry or from which `local_bases` entry
`local_root` falls under.

### Lightweight comparison (size/existence only)

```bash
python dm_integrity.py check \
  --config data_integrity_config.json \
  --experiment expname \
  [--dataset datasetname]
```

```
Experiment: expname
Upload status: done
Files: 125 good / 0 bad / 0 relocated
Recommend deletion: True
```

If an entire subdirectory has zero presence in the DM catalog (not just a
few stray files), it's called out separately rather than only showing up
as a wall of individual `LOCAL_ONLY` entries:

```
Whole subdirectories missing from Sojourner (1):
  reduced_data/rerun2
```

### MD5 checksum verification (on-demand, slower, runs in-process for the CLI)

```bash
python dm_integrity.py verify-checksums \
  --config data_integrity_config.json \
  --experiment expname
```

```
Experiment: expname
Checksums verified: 125 match
Checksums failed: 0 mismatch
Relocated (same file, different path): 0
Recommend deletion: True
```

Note: unlike the GUI's Verify MD5, the CLI's `verify-checksums` hashes
in-process (no detached job, no CPU governor) - it's meant for scripted/
one-off use, not for large experiments you'd want to walk away from.

### History of past checks

```bash
python dm_integrity.py history \
  --config data_integrity_config.json \
  --experiment expname
```

```
Records for experiment 'expname':
  2026-08-05 14:23:15: 125 good / 0 bad (recommend: True)
  2026-08-05 13:55:42: 125 good / 0 bad (recommend: True)
```

(The CLI's `history` only reads `records_dir`, not the GUI's per-beamline
shared location - use the GUI's History button for the full picture.)

## JSON Report Schema

Each Scan/Verify MD5 run saves a timestamped JSON report:

```json
{
  "experiment_name": "expname",
  "timestamp": 1722866595.123456,
  "upload_status": {
    "status": "done",
    "n_files": 125,
    "n_completed": 125,
    "n_errors": 0,
    "upload_complete": true
  },
  "file_stats": {
    "total": 125,
    "good": 125,
    "bad": 0,
    "match": 125,
    "size_mismatch": 0,
    "local_only": 0,
    "remote_only": 0,
    "checksum_mismatch": 0,
    "relocated": 0
  },
  "directory_stats": {
    "missing": [],
    "extra": []
  },
  "comparison": {
    "path/to/file1.dat": "MATCH",
    "path/to/orphan.tmp": "LOCAL_ONLY"
  },
  "checksum_results": {
    "path/to/file1.dat": "CHECKSUM_MATCH"
  },
  "relocated_files": [],
  "sojourner_status": "FULLY_LANDED",
  "sojourner_summary": "All local files have landed on Sojourner",
  "recommend_deletion": true,
  "recommendation_reason": "Upload complete and all files match (checksums verified)"
}
```

### `sojourner_status` values

- **`NO_LOCAL_FILES`**: nothing found locally to compare
- **`NOT_ON_SOJOURNER`**: every local file is `LOCAL_ONLY` - not uploaded
  yet (the expected state for a currently-running experiment)
- **`CHECKSUM_MISMATCH`**: at least one file failed MD5 verification -
  checked ahead of the two below, so a checksum failure on an
  otherwise-size-matched file isn't reported as fully landed
- **`FULLY_LANDED`**: every file matches, nothing missing on either side
- **`PARTIALLY_LANDED`**: some mix of matches, mismatches, or files only
  on one side

### `directory_stats`

A rollup derived from `comparison`, not a separate directory listing (see
`diff_directories` in `dm_integrity.py`): `"missing"` lists subdirectories
that exist locally but have *zero* files represented anywhere in the DM
catalog - a stronger, more specific signal than a pile of individual
`LOCAL_ONLY` files, which is all that would otherwise show that an entire
subdirectory never got uploaded. `"extra"` is the mirror image (present in
the catalog, absent locally - e.g. a local copy that's since been cleaned
up). A local directory with no files in it at all is never listed here in
either direction - there's nothing to have landed, so it isn't a gap.
`PARTIALLY_LANDED`'s `sojourner_summary` mentions `"missing"` directly when
non-empty; `NOT_ON_SOJOURNER` doesn't repeat it, since in that case *every*
local directory is trivially "missing" and saying so would just be noise.
(A file relocated to a different subfolder - present on both sides, just
under a different path - is a separate, per-file concept from a whole
missing subdirectory; see "Relocated Files" below.)

### File status values (`comparison`/`checksum_results`)

- **MATCH** / **SIZE_MISMATCH**: exists on both sides, sizes equal/differ
- **LOCAL_ONLY**: staged locally but not (yet) in DM's catalog
- **REMOTE_ONLY**: in DM's catalog but not found locally (already deleted
  locally, or never landed where expected - worth checking which)
- **CHECKSUM_MATCH** / **CHECKSUM_MISMATCH** / **CHECKSUM_UNKNOWN**: MD5
  agrees / disagrees / wasn't available to compare

### Relocated Files

A file can be genuinely present on **both** sides but end up as one
`LOCAL_ONLY` and one unrelated-looking `REMOTE_ONLY` entry if it moved
to a different subfolder on one side (local data reorganized after
upload, or Sojourner's layout differing from the local one) -
indistinguishable, in `comparison` alone, from an actually-missing
file. `find_relocated_files()` looks for exactly this: `LOCAL_ONLY`/
`REMOTE_ONLY` pairs sharing a basename and a recorded size, run on
every Scan and Verify MD5.

This is basename+size matching only, deliberately not
checksum-confirmed - neither side has a checksum for a `LOCAL_ONLY`/
`REMOTE_ONLY` path to compare, and hashing every candidate just to
classify it would mean an extra full pass no cheaper than Verify MD5
itself. A matched pair:

- is subtracted out of `file_stats["local_only"]`/`["remote_only"]` and
  tallied separately in `file_stats["relocated"]`/the
  `"relocated_files"` list (`comparison` itself is untouched - the
  pair's two paths still show up there as plain `LOCAL_ONLY`/`REMOTE_ONLY`)
- no longer paints the row **Red** in the GUI on its own (a
  fully-cleaned-up-after-upload experiment used to show every leftover
  `REMOTE_ONLY` file as a real problem)
- still blocks `recommend_deletion` - a basename+size match is
  evidence, not proof; nothing here is checksum-confirmed, so this tool
  never treats a relocated pair as safe to delete on that alone
- shows up in the History dialog as one combined `local -> remote` row
  (category **Relocated**) rather than two separate, seemingly
  unrelated missing-file entries

A basename shared by an unusually large number of files on either side
is skipped entirely (no attempt at exhaustive matching within that
bucket), as are zero-byte files (any two empty files would otherwise
"match").

### Deletion Safety

`"recommend_deletion": true` only if upload is complete, no
`SIZE_MISMATCH`/`LOCAL_ONLY`/`REMOTE_ONLY`/`CHECKSUM_MISMATCH` exists.
**This tool only informs and recommends - it never touches or deletes
local files.**

## Troubleshooting

**A row shows "Stalled?" or never finishes**
- The GUI flags a `RUNNING` job as **Stalled?** once its status file
  hasn't updated in 15 minutes (`_CHECKSUM_STALE_SEC` in
  `dm_integrity_gui.py`) and lets you click **Stop** to force-clear it
  without waiting for a shutdown handler that will likely never run -
  see "Persistent Checksum Jobs" and the Verify MD5/Stop bullet under
  "GUI Usage". Before force-clearing, consider whether this could be a
  single very large file: this beamline's detector files can be tens of
  GB each, and `checksum_worker.py` only reports progress once per whole
  file hashed, not per chunk - a job can legitimately show no progress
  for several minutes while genuinely alive. 900s was chosen to clear
  that case comfortably while still catching a truly-dead job (confirmed
  against two real incidents that sat `RUNNING` for 78h and 20h after
  their process had actually crashed).
- For the underlying status directly (rather than via the GUI): check
  `~<user>iduser/dm_record/checksum_status/<expid>.json` on `zion` for
  its `state` and `error_message`.
- If it's stuck at `QUEUED` with no progress ever, check for a lingering
  failed unit blocking relaunch: `ssh s1iduser@zion systemctl --user status checksum-verify@<expid>.service`.
  `launch_checksum_job` passes `--collect` specifically so finished/failed
  units clean themselves up rather than getting stuck this way; if you
  still see one, `systemctl --user reset-failed checksum-verify@<expid>.service`
  clears it manually.
- Check `/proc/<pid>/fd` on `zion` if you want to confirm a job is still
  actually doing I/O rather than dead.

**A DM query (Upload Status/Files, or Upload to DM) fails or times out**
- The error now includes the remote command's exit code and full
  stdout+stderr (previously blank for some failures) - read it before
  assuming a network/auth problem.
- If it's specifically a *timeout* on the DM catalog query and happens
  consistently for one experiment while every other experiment's
  identical query returns quickly, the most likely cause is that
  experiment already being archived in DM - check DM Station's
  Experiments/Uploads tabs. `get_upload_status`/`get_catalog_files` wait
  up to 90s/180s respectively (raised from a shared 30s default) since a
  real slow-but-legitimate response can take longer than that.

**"Upload to DM" fails with "already active or pending" / "already archived"**
- Not a failure of this tool - these are `dm-upload`'s own refusal
  messages. "Already active or pending" means an earlier upload (often
  from a previous click here) is still genuinely running - check DM
  Station's Uploads tab, or re-run Scan/Verify MD5 once it finishes.
  "Already archived" means DM refuses `--reprocess` entirely for an
  archived experiment by design - nothing to retry here; fixing
  Sojourner for an archived experiment needs DM's own un-archive/restore
  path, outside this tool's scope.

**"dm Python API is required but is not installed..."**
- Source the beamline's `dm.setup.sh` and activate `dm-user` first, or
  configure `remote_hosts`/`setup_scripts` for that beamline so the query
  runs over SSH instead.

**No experiments appear in the GUI**
- Check `settings.local_bases` points at real, readable directories, and
  that at least one subdirectory matches the `<piname>_<mon><yy>` naming
  convention.

**Records not saved / History empty**
- For Scan/Verify MD5 results: confirm `settings.checksum_hosts` has an
  entry for the row's beamline with a reachable `host`/`user`.
- Older records: confirm `settings.records_dir` is readable.

## Notes

- **Non-destructive**: informs and recommends only.
- **Standalone or combined**: `dm_integrity_gui.py` alone, or as a tab in
  `../ops_gui.py`.
