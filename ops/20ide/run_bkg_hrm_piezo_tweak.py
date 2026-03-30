#!/usr/bin/env python3
"""
HRM Background Piezo Tweaker

Reads PV names from bkg_hrm_piezo_tweak.py.

Subcommands
-----------
monitor   Continuously print the monitor PV value until Ctrl-C.
tweak     Adjust the piezo setpoint to bring the monitor PV to a target.

Usage:
    python run_bkg_hrm_piezo_tweak.py monitor                        # all 8 PVs, 1s interval
    python run_bkg_hrm_piezo_tweak.py monitor --interval 2.0
    python run_bkg_hrm_piezo_tweak.py monitor --target 100.0         # green/red coloring
    python run_bkg_hrm_piezo_tweak.py tweak   --section 1 --target 100.0
    python run_bkg_hrm_piezo_tweak.py tweak   --section 2 --target 50.0 --settle 1.0
"""

import argparse
import os
import random
import sys
import time

try:
    import epics
    _EPICS_AVAILABLE = True
except ImportError:
    _EPICS_AVAILABLE = False

# Seed values used by the dry-run fake PV store
_dry_run_store = {}

def _caget(pv, timeout=5):
    if _EPICS_AVAILABLE:
        return epics.caget(pv, timeout=timeout)
    # dry-run: return a stable random-walk value for each PV
    base = _dry_run_store.setdefault(pv, random.uniform(50.0, 150.0))
    _dry_run_store[pv] = base + random.uniform(-0.5, 0.5)
    return _dry_run_store[pv]

def _caput(pv, value, wait=False):
    if _EPICS_AVAILABLE:
        return epics.caput(pv, value, wait=wait)
    _dry_run_store[pv] = value


# ---------------------------------------------------------------------------
# Config parser
# ---------------------------------------------------------------------------

def parse_config(config_file):
    """
    Parse config file with lines of the form:
        PV_NAME   %%% COMMENT
    Sections are separated by blank lines.
    Returns a list of dicts, one per section, with keys:
        'monitor', 'voltage', 'position', 'setpoint'
    """
    sections = []
    current = {}

    with open(config_file) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                if current:
                    sections.append(current)
                    current = {}
                continue

            if '%%%' not in line:
                continue

            pv_name, _, comment = line.partition('%%%')
            pv_name = pv_name.strip()
            tag = comment.strip().upper()

            if 'NAME TO MONITOR' in tag:
                current['monitor'] = pv_name
            elif 'VOLTAGE PV' in tag:
                current['voltage'] = pv_name
            elif 'POSITION SETPOINT PV' in tag:   # must come before POSITION PV
                current['setpoint'] = pv_name
            elif 'POSITION PV' in tag:
                current['position'] = pv_name

    if current:
        sections.append(current)

    return sections


# ---------------------------------------------------------------------------
# Monitoring loop
# ---------------------------------------------------------------------------

# Ordered keys to display for each section
_PV_KEYS = ['monitor', 'voltage', 'position', 'setpoint']

_GREEN = '\033[92m'
_RED   = '\033[91m'
_RESET = '\033[0m'


def _color(val_str, val, target, tolerance):
    """Return val_str wrapped in green/red ANSI codes based on target proximity."""
    if target is None or val is None:
        return val_str
    code = _GREEN if abs(val - target) / abs(target) <= tolerance else _RED
    return f"{code}{val_str}{_RESET}"


def monitor_loop(sections, interval=1.0, targets=None, tolerance=0.05):
    """
    Continuously print all PVs from all sections until the user presses Ctrl-C.
    Monitor PV values are printed green (within tolerance of target) or red
    (outside tolerance) when --target is supplied.
    targets is a list of per-section target values (one per section).
    """
    n_pvs = sum(len(s) for s in sections)
    print(f"\n  Tracking {n_pvs} PVs across {len(sections)} section(s)")
    print(f"  Interval  : {interval}s")
    if targets is not None:
        for i, t in enumerate(targets, 1):
            print(f"  Piezo{i} target : {t:.6g}  (±{tolerance*100:.1f}%  "
                  f"{_GREEN}green = in range{_RESET} / {_RED}red = out of range{_RESET})")
    print()
    try:
        input("  Press Enter to start monitoring, or Ctrl-C to abort... ")
    except KeyboardInterrupt:
        print("\n  Aborted.")
        return
    print(f"\n  Monitoring started. Press Ctrl-C to stop.\n")

    try:
        while True:
            print(f"--- {time.strftime('%H:%M:%S')} ---")
            for i, sec in enumerate(sections, 1):
                target = targets[i - 1] if (targets and i - 1 < len(targets)) else None
                print(f"  [Piezo{i}]")
                for key in _PV_KEYS:
                    if key not in sec:
                        continue
                    pv = sec[key]
                    val = _caget(pv, timeout=5)
                    val_str = f"{val:.6g}" if val is not None else "DISCONNECTED"
                    if key == 'monitor':
                        val_str = _color(val_str, val, target, tolerance)
                    print(f"    {key:8s} : {pv:<42s} = {val_str}")
                print()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Monitoring stopped.")


# ---------------------------------------------------------------------------
# Tweaking logic
# ---------------------------------------------------------------------------

def _read(pv_name, label):
    val = epics.caget(pv_name, timeout=5)
    if val is None:
        print(f"ERROR: cannot read {label} PV: {pv_name}")
        sys.exit(1)
    return val


def tweak_piezo(monitor_pv, setpoint_pv, target,
                step=0.01, max_change=0.05, tolerance=0.05, settle=0.5):
    """
    Tweak setpoint_pv in 'step' increments until monitor_pv is within
    'tolerance' (fractional) of 'target', or the cumulative absolute
    displacement from the starting position reaches 'max_change'.

    Returns True if the target was reached.
    """
    current_val = _read(monitor_pv, 'monitor')

    print()
    print(f"  Monitor PV  : {monitor_pv}")
    print(f"  Setpoint PV : {setpoint_pv}")
    print(f"  Current     : {current_val:.6g}")
    print(f"  Target      : {target:.6g}")
    print(f"  Tolerance   : {tolerance*100:.1f}%")
    print(f"  Max change  : {max_change:.4f}")
    print(f"  Step        : {step:.4f}")
    print(f"  Settle time : {settle}s")
    print()

    rel_err = abs(current_val - target) / abs(target)
    if rel_err <= tolerance:
        print(f"  Already within tolerance ({rel_err*100:.2f}%). Nothing to do.")
        return True

    start_pos = _read(setpoint_pv, 'setpoint')
    print(f"  Start pos   : {start_pos:.6f}")
    print(f"  {'Step':>6}  {'Position':>10}  {'Delta':>8}  {'Monitor':>12}  {'|Error|':>12}")
    print(f"  {'-'*6}  {'-'*10}  {'-'*8}  {'-'*12}  {'-'*12}")

    current_pos = start_pos
    prev_err = abs(current_val - target)
    direction = None  # determined by probe step

    # --- Probe: one step in positive direction ---
    probe_pos = round(current_pos + step, 9)
    if abs(probe_pos - start_pos) > max_change:
        print("  Cannot take even one step without exceeding max-delta. Aborting.")
        return False

    _caput(setpoint_pv, probe_pos, wait=True)
    time.sleep(settle)
    probe_val = _read(monitor_pv, 'monitor')
    probe_err = abs(probe_val - target)
    delta = probe_pos - start_pos
    print(f"  {'probe':>6}  {probe_pos:10.6f}  {delta:+8.4f}  {probe_val:12.6g}  {probe_err:12.6g}", end="")

    if probe_err < prev_err:
        direction = +1
        print("  → +")
        current_pos = probe_pos
        current_val = probe_val
        prev_err = probe_err
        step_n = 1
    else:
        direction = -1
        print("  → undo, try −")
        # Revert probe step
        _caput(setpoint_pv, start_pos, wait=True)
        time.sleep(settle)
        current_pos = start_pos
        current_val = _read(monitor_pv, 'monitor')
        prev_err = abs(current_val - target)
        step_n = 0

    # --- Main loop ---
    while True:
        rel_err = abs(current_val - target) / abs(target)
        if rel_err <= tolerance:
            print(f"\n  Target reached. Error = {rel_err*100:.2f}%")
            break

        next_pos = round(current_pos + direction * step, 9)
        delta = abs(next_pos - start_pos)
        if delta > max_change:
            print(f"\n  Max delta ({max_change}) reached. Stopping.")
            break

        step_n += 1
        _caput(setpoint_pv, next_pos, wait=True)
        time.sleep(settle)
        current_val = _read(monitor_pv, 'monitor')
        current_err = abs(current_val - target)
        signed_delta = next_pos - start_pos
        print(f"  {step_n:>6}  {next_pos:10.6f}  {signed_delta:+8.4f}  {current_val:12.6g}  {current_err:12.6g}")

        if current_err >= prev_err:
            print("  Error no longer decreasing. Stopping.")
            break

        prev_err = current_err
        current_pos = next_pos

    # --- Summary ---
    final_val = _read(monitor_pv, 'monitor')
    final_pos = _read(setpoint_pv, 'setpoint')
    rel_err = abs(final_val - target) / abs(target)
    print()
    print(f"  Final pos   : {final_pos:.6f}  (Δ = {final_pos - start_pos:+.4f})")
    print(f"  Final val   : {final_val:.6g}")
    print(f"  Target      : {target:.6g}")
    print(f"  Final error : {rel_err*100:.2f}%")
    return rel_err <= tolerance


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _default_config():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, 'bkg_hrm_piezo_tweak.py')


def _load_all_sections(config):
    """Parse config and return all sections."""
    if not os.path.exists(config):
        print(f"ERROR: Config file not found: {config}")
        sys.exit(1)
    sections = parse_config(config)
    if not sections:
        print("ERROR: No valid sections found in config file.")
        sys.exit(1)
    return sections


def _load_section(args):
    """Parse config and return the single chosen section dict."""
    sections = _load_all_sections(args.config)
    idx = args.section - 1
    if not (0 <= idx < len(sections)):
        print(f"ERROR: Section {args.section} not found "
              f"(config has {len(sections)} section(s)).")
        sys.exit(1)
    sec = sections[idx]
    print(f"Section {args.section} PVs:")
    for k, v in sec.items():
        print(f"  {k:10s}: {v}")
    for key in ('monitor', 'setpoint'):
        if key not in sec:
            print(f"ERROR: Section {args.section} is missing '{key}' PV.")
            sys.exit(1)
    return sec


def main():
    parser = argparse.ArgumentParser(
        description="HRM piezo monitor / tweaker.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # --- monitor subcommand ---
    p_mon = sub.add_parser('monitor',
                           help='Continuously print all 8 PVs until Ctrl-C.',
                           formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p_mon.add_argument('--config', default=_default_config(),
                       help='Path to PV config file')
    p_mon.add_argument('--interval', type=float, default=1.0,
                       help='Polling interval in seconds')
    p_mon.add_argument('--target', type=str, required=True,
                       help='Comma-separated targets for Piezo1,Piezo2 (e.g. 100.0,80.0)')
    p_mon.add_argument('--tolerance', type=float, default=5.0,
                       help='Tolerance in %% around target for green/red coloring')
    p_mon.add_argument('--dry-run', action='store_true',
                       help='Use fake values instead of real EPICS PVs')

    # --- tweak subcommand ---
    p_twk = sub.add_parser('tweak',
                           help='Adjust piezo setpoint to reach a target value.',
                           formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p_twk.add_argument('--config', default=_default_config(),
                       help='Path to PV config file')
    p_twk.add_argument('--section', type=int, default=1,
                       help='Config section: 1 (piezo1) or 2 (piezo2)')
    p_twk.add_argument('--target', type=float, required=True,
                       help='Target value for the monitor PV')
    p_twk.add_argument('--step', type=float, default=0.01,
                       help='Piezo position step size')
    p_twk.add_argument('--max-change', type=float, default=0.05,
                       help='Max cumulative absolute displacement from start')
    p_twk.add_argument('--tolerance', type=float, default=5.0,
                       help='Acceptable error as a percentage of target')
    p_twk.add_argument('--settle', type=float, default=0.5,
                       help='Seconds to wait after each step')

    args = parser.parse_args()

    if args.command == 'monitor':
        if not args.dry_run and not _EPICS_AVAILABLE:
            print("ERROR: pyepics not installed. Use --dry-run to test without EPICS.")
            sys.exit(1)
        try:
            targets = [float(v.strip()) for v in args.target.split(',')]
        except ValueError:
            print("ERROR: --target must be two comma-separated numbers, e.g. --target 100.0,80.0")
            sys.exit(1)
        if len(targets) != 2:
            print(f"ERROR: --target requires exactly 2 values (got {len(targets)}), "
                  f"e.g. --target 100.0,80.0")
            sys.exit(1)
        sections = _load_all_sections(args.config)
        monitor_loop(sections, interval=args.interval,
                     targets=targets, tolerance=args.tolerance / 100.0)

    elif args.command == 'tweak':
        sec = _load_section(args)
        success = tweak_piezo(
            monitor_pv=sec['monitor'],
            setpoint_pv=sec['setpoint'],
            target=args.target,
            step=args.step,
            max_change=args.max_change,
            tolerance=args.tolerance / 100.0,
            settle=args.settle,
        )
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
