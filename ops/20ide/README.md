# HRM Background Piezo Monitor & Tweaker

## Overview

This package provides tools to monitor and adjust piezo setpoints in the 20-ID High-Resolution Modulation (HRM) background hutch. The system consists of two main components:

- **bkg_hrm_piezo_tweak.py** — Configuration file defining PV names for piezo control and monitoring
- **run_bkg_hrm_piezo_tweak.py** — CLI tool with two subcommands: `monitor` and `tweak`

## Configuration Setup

### bkg_hrm_piezo_tweak.py

This file maps EPICS Process Variables (PVs) to piezo sections. Each section is separated by blank lines and contains four annotated PVs:

```python
PIEZO_SECTION_1_MONITOR      %%% NAME TO MONITOR
PIEZO_SECTION_1_VOLTAGE      %%% VOLTAGE PV
PIEZO_SECTION_1_POSITION     %%% POSITION PV
PIEZO_SECTION_1_SETPOINT     %%% POSITION SETPOINT PV

PIEZO_SECTION_2_MONITOR      %%% NAME TO MONITOR
PIEZO_SECTION_2_VOLTAGE      %%% VOLTAGE PV
PIEZO_SECTION_2_POSITION     %%% POSITION PV
PIEZO_SECTION_2_SETPOINT     %%% POSITION SETPOINT PV
```

The `%%%` separator marks the comment/tag that identifies each PV's role:
- **NAME TO MONITOR**: The output PV value to observe and control
- **VOLTAGE PV**: The voltage applied to the piezo (informational)
- **POSITION PV**: The current physical position of the piezo
- **POSITION SETPOINT PV**: The setpoint value to adjust to reach the target

## Usage

### Monitor Mode

Continuously poll all configured PVs at regular intervals:

```bash
# Monitor all 8 PVs (4 per section × 2 sections) every second
python run_bkg_hrm_piezo_tweak.py monitor

# Monitor with custom interval (2 seconds)
python run_bkg_hrm_piezo_tweak.py monitor --interval 2.0

# Dry-run mode (uses simulated values instead of real EPICS PVs)
python run_bkg_hrm_piezo_tweak.py monitor --dry-run

# Custom config file
python run_bkg_hrm_piezo_tweak.py monitor --config /path/to/config.py
```

**Output Example:**
```
  Tracking 8 PVs across 2 section(s)
  Interval : 1s
  Press Ctrl-C to stop.

--- 14:32:45 ---
  [S1] monitor  : 20IDE:bkg:HRM:mon:PV              = 98.234
  [S1] voltage  : 20IDE:bkg:HRM:volt:PV            = 45.67
  [S1] position : 20IDE:bkg:HRM:pos:PV             = 0.523
  [S1] setpoint : 20IDE:bkg:HRM:setpt:PV           = 0.520
  [S2] monitor  : 20IDE:bkg:HRM2:mon:PV            = 102.456
  ...
```

### Tweak Mode

Adjust a piezo setpoint to bring the monitored value to a target:

```bash
# Adjust section 1 to target 100.0
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0

# With custom step size and tolerance
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0 \
    --step 0.02 --tolerance 2.0

# With longer settle time between steps
python run_bkg_hrm_piezo_tweak.py tweak --section 2 --target 50.0 --settle 1.0

# Dry-run mode
python run_bkg_hrm_piezo_tweak.py tweak --dry-run --section 1 --target 100.0 \
    --target 100.0
```

## Tweak Algorithm

The `tweak` subcommand uses a **probe-and-reverse** optimization strategy:

### Phase 1: Direction Probe
1. Reads the current monitor PV value
2. Compares to target; if already within tolerance, exits with success
3. Attempts one positive step in the setpoint
4. Measures the error change:
   - If error improved → move in positive direction (step_n = 1)
   - If error worsened → revert and try negative direction (step_n = 0)

### Phase 2: Iterative Adjustment
1. Continues stepping in the determined direction
2. Checks if error is **decreasing** — if error increases or plateaus, stops
3. Enforces **max-delta** constraint — stops if cumulative displacement exceeds limit
4. Enforces **tolerance** — stops if relative error ≤ tolerance%
5. Settles for N seconds after each step before re-reading

### Phase 3: Summary
Reports final position, final monitor value, and final error percentage.

## Parameters

### Monitor Options
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--config` | str | bkg_hrm_piezo_tweak.py | Path to config file |
| `--interval` | float | 1.0 | Polling interval in seconds |
| `--dry-run` | flag | False | Use simulated PVs (no EPICS required) |

### Tweak Options
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--config` | str | bkg_hrm_piezo_tweak.py | Path to config file |
| `--section` | int | 1 | Config section (1 or 2) |
| `--target` | float | (required) | Target value for monitor PV |
| `--step` | float | 0.01 | Setpoint step size per iteration |
| `--max-change` | float | 0.05 | Max cumulative displacement from start |
| `--tolerance` | float | 5.0 | Acceptable error as % of target |
| `--settle` | float | 0.5 | Seconds to wait after each step |
| `--dry-run` | flag | False | Use simulated PVs (no EPICS required) |

## Requirements

- Python 3.9+
- **pyepics** (optional, required only for real EPICS connection; not needed for `--dry-run`)

### Option A: conda environment (recommended)

An `environment.yml` is provided at the repo root for a reproducible setup:

```bash
# From the repo root
conda env create -f environment.yml
conda activate hrm-piezo
```

### Option B: pip only
```bash
pip install pyepics
```

## Dry-Run Mode

For testing without EPICS connection, use `--dry-run`:
- Simulates random walk behavior for each PV
- Allows testing tweaking logic without hardware
- Useful for validation before running on real beamline hardware

```bash
python run_bkg_hrm_piezo_tweak.py monitor --dry-run
python run_bkg_hrm_piezo_tweak.py tweak --dry-run --section 1 --target 100.0
```

## Exit Codes

- `0` — Success (for `tweak`, target was reached or monitor exited cleanly)
- `1` — Failure (for `tweak`, target was not reached within constraints; or config error)

## Examples

### Scenario 1: Quick monitoring check
```bash
python run_bkg_hrm_piezo_tweak.py monitor --interval 0.5
```
Polls all PVs every 0.5 seconds. Press Ctrl-C to stop.

### Scenario 2: Tweak with tight tolerance
```bash
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0 \
    --tolerance 1.0 --step 0.005 --max-change 0.1
```
Fine-tuning: small steps, strict tolerance, larger allowed range.

### Scenario 3: Tweak with quick broad search
```bash
python run_bkg_hrm_piezo_tweak.py tweak --section 2 --target 50.0 \
    --step 0.02 --tolerance 5.0 --settle 0.2
```
Faster adjustment with looser tolerance and shorter settle times.

### Scenario 4: Test configuration
```bash
python run_bkg_hrm_piezo_tweak.py monitor --dry-run --interval 2.0
```
Simulates PV polling without EPICS to verify config and script logic.

## Troubleshooting

### "ERROR: cannot read X PV"
- Connection to EPICS is down
- PV name in config is incorrect
- Use `--dry-run` to test without EPICS

### "ERROR: Config file not found"
- Default config path is incorrect
- Explicitly pass `--config /path/to/bkg_hrm_piezo_tweak.py`

### "ERROR: Section N not found"
- Config has fewer sections than requested
- Check number of blank-line-separated blocks in config file

### "ERROR: Section N is missing 'monitor' or 'setpoint' PV"
- A section is missing required PV definitions
- Verify all sections have both NAME TO MONITOR and POSITION SETPOINT PV tags

### "Max delta reached. Stopping."
- Piezo cannot reach target within `--max-change` constraint
- Increase `--max-change` or adjust `--target`

### "Error no longer decreasing"
- Algorithm hit a plateau; target may be unreachable
- Verify target value is physically achievable
- Try different `--step` size or `--settle` time

## Technical Notes

### Precision
- Setpoint values are rounded to 9 decimal places to avoid floating-point artifacts
- Error is computed as relative error: `|current - target| / |target| × 100%`

### Safety Features
- **Max-change enforcement**: Prevents excessive piezo displacement
- **Direction probe**: Automatically determines correct adjustment direction
- **Error monitoring**: Stops if error stops decreasing (plateau detection)
- **Settle time**: Allows PV to stabilize before re-reading

### PV State After Tweak
- Final setpoint remains at the adjusted value
- Use `monitor` subcommand to verify post-adjustment state
- To revert a tweak, run another tweak with the original target or manually adjust

## Related Documentation

- EPICS Channel Access documentation: http://www.aps.anl.gov/epics/
- 20-ID beamline documentation: [internal reference]
- HRM background hutch design: [internal reference]
