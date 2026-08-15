# Data Integrity Monitor

Verifies that data uploaded from s1c (hutch-local staging) to APS Data Management (Sojourner) is complete and uncorrupted. Provides lightweight (file size/existence) and on-demand (MD5 checksum) integrity checks, plus timestamped JSON records per experiment.

## Setup

**Important:** This tool requires the APS Data Management (DM) Python API, which is **not** part of the shared `ops` conda environment. The DM API must be activated via beamline-specific setup:

```bash
# Example for 1-ID (path may differ for your beamline)
source /dm/1id/etc/dm.setup.sh
conda activate dm-user
```

Once activated, the shared `ops` environment can be used for the GUI and CLI:

```bash
conda activate ops
python dm_integrity.py check --config data_integrity_config.json --experiment expname
python dm_integrity_gui.py
```

If the DM environment is not set up, both the CLI and GUI will fail with a clear error pointing to this prerequisite.

## Configuration

**`data_integrity_config.json`**:

```json
{
  "settings": {
    "station_name": "SOJOURNER",
    "records_dir": "./records"
  },
  "experiments": [
    {
      "name": "experiment_name",
      "local_root": "/home/beams/PARKJS/mnt/s1c/experiment_name",
      "dataset": null,
      "running": false
    }
  ]
}
```

- **`station_name`**: DM storage system name (default: "SOJOURNER" for APS)
- **`records_dir`**: Directory for timestamped JSON reports; auto-created per experiment
- **`experiments`** list:
  - **`name`**: Experiment name (as used in DM)
  - **`local_root`**: Local staging directory (typically under `/home/beams/PARKJS/mnt/s1c/`)
  - **`dataset`** (optional): Specific dataset within the experiment; if omitted, checks all files
  - **`running`** (optional): If `true`, experiment name is shown in **bold** in the GUI to indicate active collection

## CLI Usage

### Lightweight comparison (size/existence only)

```bash
python dm_integrity.py check \
  --config data_integrity_config.json \
  --experiment expname \
  [--dataset datasetname]
```

Output example:
```
Experiment: expname
Upload status: done
Files: 125 good / 0 bad
Recommend deletion: True
```

### MD5 checksum verification (on-demand, slower)

```bash
python dm_integrity.py verify-checksums \
  --config data_integrity_config.json \
  --experiment expname
```

Output example:
```
Experiment: expname
Checksums verified: 125 match
Checksums failed: 0 mismatch
Recommend deletion: True
```

### History of past checks

```bash
python dm_integrity.py history \
  --config data_integrity_config.json \
  --experiment expname
```

Output example:
```
Records for experiment 'expname':
  2026-08-05 14:23:15: 125 good / 0 bad (recommend: True)
  2026-08-05 13:55:42: 125 good / 0 bad (recommend: True)
```

## GUI Usage

### Standalone

```bash
python dm_integrity_gui.py
```

### Combined with disk_monitor and pv_logger

See `../ops_gui.py`.

## Dashboard View

The GUI shows a **dashboard of the 10 most recent experiments** (sorted by experiment name, most recent first):

- **Expid column**: Bold font indicates currently-running experiment
- **Upload Status**: Pending/Running/Done/Failed
- **Files column**: Shows "X good / Y bad" with color coding:
  - **Green**: All files match, upload complete — safe to delete
  - **Yellow**: Upload in progress or minor issues requiring attention
  - **Red**: Actual problems (file mismatches, checksums don't match)
  - **Orange**: Non-critical missing files (e.g., Thumb.db)
- **Check button**: Runs lightweight size/existence comparison, updates row and saves record
- **Verify button**: Runs MD5 checksum verification on matching files (slower, on-demand)
- **History button**: Shows past 10 records for this experiment

## JSON Report Schema

Each check/verify run saves a timestamped JSON report under `records/<experiment_name>/<timestamp>.json`:

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
    "checksum_mismatch": 0
  },
  "comparison": {
    "path/to/file1.dat": "MATCH",
    "path/to/file2.dat": "MATCH",
    "path/to/orphan.tmp": "LOCAL_ONLY"
  },
  "checksum_results": {
    "path/to/file1.dat": "CHECKSUM_MATCH",
    "path/to/file2.dat": "CHECKSUM_MATCH"
  },
  "recommend_deletion": true,
  "recommendation_reason": "Upload complete and all files match (checksums verified)"
}
```

### File Status Values

- **MATCH**: File exists locally and on DM, sizes are equal
- **SIZE_MISMATCH**: File exists on both, but sizes differ
- **LOCAL_ONLY**: File staged locally but not (yet) in DM catalog
- **REMOTE_ONLY**: File in DM catalog but not on local staging (likely already deleted locally)
- **CHECKSUM_MATCH**: MD5 hash matches DM's catalog value
- **CHECKSUM_MISMATCH**: MD5 hash differs from DM's catalog value
- **CHECKSUM_UNKNOWN**: File size matches but no checksum data available

### Deletion Safety

`"recommend_deletion": true` **only if**:
1. Upload is complete (`status == "done"` and `nProcessingErrors == 0`)
2. All files are `MATCH` (no `SIZE_MISMATCH`, `LOCAL_ONLY`, or `REMOTE_ONLY`)
3. If checksums were verified, all must be `CHECKSUM_MATCH`
4. No files are flagged `CHECKSUM_MISMATCH`

**This tool only recommends—it never deletes.** Use the report to make safe deletion decisions.

## How It Works

### Lightweight Check (default)

1. Queries DM's upload status via `ExperimentDaqApi.listUploadRecords()`
2. Fetches remote file metadata (name, size, MD5) via `FileCatApi.getExperimentFiles()`
3. Scans local staging directory recursively via `os.walk()`
4. Compares: file exists on both sides? If so, are sizes equal?
5. Classifies each file and builds a summary report
6. Saves report as timestamped JSON

### Checksum Verification (explicit, slower)

1. After lightweight compare, MD5-hashes only the files marked `MATCH`
2. Compares computed hashes against DM's catalog values
3. Updates report with checksum results
4. If all hashes match and upload is complete, sets `recommend_deletion: true`

### Multi-Check History

Each experiment may have many records (daily checks, before major deletions, etc.). The GUI and CLI history commands show the 10 most recent, so you can track how file status evolves over time.

## DM API Details (for troubleshooting)

The tool uses three main DM web service APIs:

- **`dm.daq_web_service.api.experimentDaqApi.ExperimentDaqApi.listUploadRecords(queryDict={"experimentName": name})`**
  - Returns upload history; tool picks the latest record
  - `status` values: `"pending"`, `"running"`, `"finalizing"`, `"done"`, `"failed"`, `"aborted"`
  - Tool considers upload complete iff `status == "done"` and `nProcessingErrors == 0`

- **`dm.cat_web_service.api.fileCatApi.FileCatApi.getExperimentFiles(experimentName)`**
  - Returns list of `FileMetadata` dicts; each has `fileSize`, `md5Sum`, `experimentFilePath`
  - Reflects metadata captured at upload time (not live stat)

- **`dm.ds_web_service.api.fileDsApi.FileDsApi.statFile(..., retrieveMd5Sum=True)`**
  - Not currently used by this tool; available for future live re-verification if needed

## Troubleshooting

**"dm Python API is required but is not installed..."**
- Source the beamline's `dm.setup.sh` and activate `dm-user` conda environment before running

**No experiments appear in the GUI**
- Check `data_integrity_config.json` is in the same directory as the script, or pass `--config /path/to/config.json`
- Verify the `experiments` list in config is not empty

**Check/Verify buttons don't work**
- Ensure DM environment is still active (in a separate terminal, `conda activate dm-user` is still running)
- Check error message in status bar at bottom of panel

**Records not saved**
- Verify `records_dir` in config exists or is writable

## Notes

- **Non-destructive**: This tool only informs and recommends. It never touches local files or issues delete commands. You decide what to do based on the report.
- **Standalone or combined**: Can run as `dm_integrity_gui.py` alone or as a tab in `../ops_gui.py` alongside disk_monitor and pv_logger.
- **Experimental on this host**: This dev machine has only a 20ID DM station setup, not 1ID. Real end-to-end testing with a live 1-ID experiment happens on a 1-ID DM-enabled host.
