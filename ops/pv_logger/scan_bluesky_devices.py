#!/usr/bin/env python3
"""Cross-check pv_master_list_s1.json/pv_master_list_s20.json against the
beamlines' actual Bluesky instrument device definitions.

Read-only, report-only: statically parses the instrument's *_devices/*.py
files (stdlib `ast`, no ophyd/bluesky/apstools import - see the plan this
was built from for why) and resolves the PVs of "motor stack" devices
(anything built from generic_motors.py's make_n_axes_device factory, plus
FoilDevice/AttenuatorDevice/single-motor classes) to find:

  - devices bluesky defines that aren't yet in the master list (candidates
    to add)
  - master-list PVs that don't show up among this scan's resolved PVs
    (POSSIBLY stale/renamed - NOT a removal recommendation, since most
    master-list PVs are legitimately out of this pass's motor-stack-only
    scope: detectors, scalers, calc records, and the many device classes
    this script doesn't attempt to resolve)

Nothing is written to the master list files. Run it, read the report,
decide what (if anything) to merge in a follow-up pass.
"""
import argparse
import ast
import datetime
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import pv_logger as pl  # noqa: E402

# Classes whose first positional arg (or a same-named kwarg) is already
# the complete PV - no prefix/suffix combination needed.
SINGLE_MOTOR_CLASSES = {
    "MPEMotor", "AMCIMotor", "ConicalMotor", "ACSMotor", "RotationMotor",
    "EpicsMotor", "EpicsSignal", "EpicsSignalRO",
}

NONLITERAL = object()  # sentinel: a value existed but wasn't a literal string


def parse_file(path):
    with open(path) as f:
        source = f.read()
    return ast.parse(source, filename=path)


def iter_module_level_assigns(body):
    """Yield (Assign node) for every module-level assignment, descending
    into top-level If/Try/With bodies (conditional device definitions) but
    never into FunctionDef/ClassDef/For/While - those aren't instrument
    device instantiations."""
    for node in body:
        if isinstance(node, ast.Assign):
            yield node
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            for attr in ("body", "orelse", "finalbody"):
                sub = getattr(node, attr, None)
                if sub:
                    yield from iter_module_level_assigns(sub)


def assign_target_name(assign):
    """The plain variable name a module-level assignment targets, or None
    for anything more complex (tuple unpacking, attribute targets) - those
    aren't how instrument devices get defined here."""
    if len(assign.targets) != 1:
        return None
    target = assign.targets[0]
    return target.id if isinstance(target, ast.Name) else None


def call_func_name(call):
    """The plain function name a Call node invokes (ast.Name only - an
    attribute call like module.Class(...) is left unresolved rather than
    guessed at)."""
    return call.func.id if isinstance(call.func, ast.Name) else None


def literal_str(node):
    """The string value of an ast.Constant str node, or None if node is
    None, or NONLITERAL if node exists but isn't a plain string literal."""
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return NONLITERAL


def get_arg(call, keyword, positional_index):
    """A Call's argument by keyword name first, falling back to a
    positional index - mirrors Python's own positional-or-keyword
    parameter binding for the constructors this script models."""
    for kw in call.keywords:
        if kw.arg == keyword:
            return literal_str(kw.value)
    if positional_index is not None and len(call.args) > positional_index:
        return literal_str(call.args[positional_index])
    return None


def literal_str_list(node):
    """The list of string values of an ast.List of Constant strs, or None
    if node isn't a literal list of literal strings throughout."""
    if not isinstance(node, ast.List):
        return None
    values = []
    for elt in node.elts:
        s = literal_str(elt)
        if s is None or s is NONLITERAL:
            return None
        values.append(s)
    return values


def find_stack_classes(paths):
    """Pass 1: scan the given files for `Var = make_n_axes_device("Name",
    [axes...], motor_cls, ...)` assignments. Returns {assigned_var_name:
    [axis, ...]}."""
    registry = {}
    for path in paths:
        if not os.path.isfile(path):
            continue
        tree = parse_file(path)
        for assign in iter_module_level_assigns(tree.body):
            var_name = assign_target_name(assign)
            if var_name is None or not isinstance(assign.value, ast.Call):
                continue
            call = assign.value
            if call_func_name(call) != "make_n_axes_device":
                continue
            axes = get_arg_list(call, "axes", 1)
            if axes is not None:
                registry[var_name] = axes
    return registry


def get_arg_list(call, keyword, positional_index):
    for kw in call.keywords:
        if kw.arg == keyword:
            return literal_str_list(kw.value)
    if len(call.args) > positional_index:
        return literal_str_list(call.args[positional_index])
    return None


def resolve_stack_device(call, axes, var_name, path, lineno):
    """A device built from an N-axes stack class - mirrors NAxesDevice.
    __init__'s own Px/Mx defaulting logic in generic_motors.py exactly:
    Px defaults to P, Mx defaults to f"m{axis}"."""
    P = get_arg(call, "P", 0)
    name = get_arg(call, "name", None) or var_name
    if P is NONLITERAL:
        return [unresolved_entry(var_name, "non-literal P", path, lineno)]

    entries = []
    for axis in axes:
        px = get_arg(call, f"P{axis}", None)
        mx = get_arg(call, f"M{axis}", None)
        px = P if px is None else px
        mx = f"m{axis}" if mx is None else mx
        if px is NONLITERAL or mx is NONLITERAL or px is None or mx is None:
            entries.append(unresolved_entry(f"{var_name}.{axis}", "non-literal axis PV", path, lineno))
            continue
        entries.append({
            "name": f"{name} {axis}", "pv": f"{px}{mx}",
            "source": f"{path}:{lineno}", "var": var_name,
        })
    return entries


def resolve_foil_or_atten(call, var_name, path, lineno):
    prefix = get_arg(call, "prefix", 0)
    motor_pv = get_arg(call, "motor_pv", 1)
    name = get_arg(call, "name", None) or var_name
    if NONLITERAL in (prefix, motor_pv) or None in (prefix, motor_pv):
        return [unresolved_entry(var_name, "non-literal prefix/motor_pv", path, lineno)]
    return [{
        "name": f"{name} rz", "pv": f"{prefix}{motor_pv}",
        "source": f"{path}:{lineno}", "var": var_name,
    }]


def resolve_single_motor(call, var_name, path, lineno):
    pv = get_arg(call, "prefix", 0)
    name = get_arg(call, "name", None) or var_name
    if pv is NONLITERAL or pv is None:
        return [unresolved_entry(var_name, "non-literal PV", path, lineno)]
    return [{"name": name, "pv": pv, "source": f"{path}:{lineno}", "var": var_name}]


def resolve_zonda(call, var_name, path, lineno):
    prefix = get_arg(call, "prefix", 0)
    setpoint = get_arg(call, "_setpoint", 1)
    readback = get_arg(call, "_readback", 2)
    name = get_arg(call, "name", None) or var_name
    if NONLITERAL in (prefix, setpoint, readback) or None in (prefix, setpoint, readback):
        return [unresolved_entry(var_name, "non-literal prefix/setpoint/readback", path, lineno)]
    return [
        {"name": f"{name} setpoint", "pv": f"{prefix}{setpoint}", "source": f"{path}:{lineno}", "var": var_name},
        {"name": f"{name} readback", "pv": f"{prefix}{readback}", "source": f"{path}:{lineno}", "var": var_name},
    ]


def unresolved_entry(var_name, reason, path, lineno):
    return {"var": var_name, "reason": reason, "source": f"{path}:{lineno}"}


def find_device_instantiations(paths, stack_registry):
    """Pass 2: scan the given beamline device files for module-level
    `var = ClassName(...)` calls and resolve what we can. Returns
    (resolved, unresolved) - resolved entries have name/pv/source/var;
    unresolved entries have var/reason/source (or var/class/source for a
    genuinely unmodeled class)."""
    resolved, unresolved = [], []
    for path in paths:
        if not os.path.isfile(path):
            continue
        tree = parse_file(path)
        for assign in iter_module_level_assigns(tree.body):
            var_name = assign_target_name(assign)
            if var_name is None or not isinstance(assign.value, ast.Call):
                continue
            call = assign.value
            func_name = call_func_name(call)
            lineno = assign.lineno
            if func_name is None:
                continue

            if func_name in stack_registry:
                out = resolve_stack_device(call, stack_registry[func_name], var_name, path, lineno)
            elif func_name in ("FoilDevice", "AttenuatorDevice"):
                out = resolve_foil_or_atten(call, var_name, path, lineno)
            elif func_name in SINGLE_MOTOR_CLASSES:
                out = resolve_single_motor(call, var_name, path, lineno)
            elif func_name == "ZondaMotor":
                out = resolve_zonda(call, var_name, path, lineno)
            elif func_name == "make_n_axes_device":
                continue  # already handled in Pass 1, not itself a device instance
            else:
                unresolved.append({"var": var_name, "class": func_name, "source": f"{path}:{lineno}"})
                continue

            for entry in out:
                (unresolved if "reason" in entry else resolved).append(entry)
    return resolved, unresolved


def list_py_files(directory):
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f) for f in os.listdir(directory)
        if f.endswith(".py")
    )


def scan_beamline(generic_motors_path, beamline_device_dirs):
    """Run all three passes for one beamline (s20 combines two device
    dirs - s20ide_devices + s20idd_devices - into one scan, matching
    pv_master_list_s20.json covering both hutches)."""
    device_files = []
    for d in beamline_device_dirs:
        device_files.extend(list_py_files(d))

    registry = find_stack_classes([generic_motors_path] + device_files)
    resolved, unresolved = find_device_instantiations(device_files, registry)
    return resolved, unresolved


def base_pv(pv):
    """Strip a trailing .RBV - resolved motor-stack PVs are the bare motor
    record base address (e.g. "1idb:m47"), while the master list stores
    the motor's readback field (e.g. "1idb:m47.RBV"); without this, every
    single motor-stack PV would mismatch on principle regardless of
    whether the hardware actually matches."""
    return pv[:-4] if pv.endswith(".RBV") else pv


def cross_check(resolved, master_list_path):
    cfg = pl.load_config(master_list_path)
    master_pvs = {e["pv"] for e in cfg.get("pvs", [])}
    master_base_pvs = {base_pv(pv) for pv in master_pvs}
    resolved_pvs = {e["pv"] for e in resolved}
    resolved_rbv_pvs = {pv + ".RBV" for pv in resolved_pvs}

    new_devices = [e for e in resolved if e["pv"] not in master_pvs and e["pv"] not in master_base_pvs]
    not_found = [
        e for e in cfg.get("pvs", [])
        if e["pv"] not in resolved_pvs and e["pv"] not in resolved_rbv_pvs
    ]
    return new_devices, not_found


def format_report(beamline_name, resolved, unresolved, new_devices, not_found):
    lines = [f"=== {beamline_name} ===", ""]

    lines.append(f"Resolved motor-stack devices: {len(resolved)}")
    lines.append(f"New (not in master list), {len(new_devices)}:")
    for e in sorted(new_devices, key=lambda e: e["name"]):
        lines.append(f"  {e['name']:30} {e['pv']:25} ({e['source']})")
    lines.append("")

    lines.append(f"In master list but NOT found among resolved motor-stack PVs, {len(not_found)}")
    lines.append("(NOT a removal recommendation - most of these are legitimately out of scope: "
                  "detectors, scalers, calc records, or a device class this pass doesn't resolve)")
    for e in sorted(not_found, key=lambda e: (e.get("group", ""), e["name"])):
        lines.append(f"  {e.get('group', ''):30} {e['name']:20} {e['pv']}")
    lines.append("")

    class_counts = {}
    for e in unresolved:
        if "class" in e:
            class_counts[e["class"]] = class_counts.get(e["class"], 0) + 1
    lines.append(f"Unresolved (out of scope for this pass), {len(unresolved)} instances, "
                 f"{len(class_counts)} distinct classes:")
    for cls, count in sorted(class_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {cls:30} x{count}")
    non_literal = [e for e in unresolved if "reason" in e]
    if non_literal:
        lines.append(f"  ({len(non_literal)} recognized-class instances skipped for non-literal PV args)")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    default_root = "/home/beams/S20IDUSER/bluesky/instrument/devices"
    parser.add_argument("--devices-root", default=default_root,
                         help=f"Path to the bluesky instrument's devices/ directory (default: {default_root} - "
                              "the S20IDUSER checkout, which mirrors s1id_devices too and is readable without "
                              "s1iduser access; see the plan this script was built from)")
    parser.add_argument("--out", default=None, help="Also write the report to this path (default: "
                         "a timestamped file next to this script)")
    args = parser.parse_args()

    generic_motors_path = os.path.join(args.devices_root, "generic_motors.py")

    s1_resolved, s1_unresolved = scan_beamline(
        generic_motors_path, [os.path.join(args.devices_root, "s1id_devices")])
    s20_resolved, s20_unresolved = scan_beamline(
        generic_motors_path,
        [os.path.join(args.devices_root, "s20ide_devices"), os.path.join(args.devices_root, "s20idd_devices")])

    s1_new, s1_not_found = cross_check(s1_resolved, os.path.join(SCRIPT_DIR, "pv_master_list_s1.json"))
    s20_new, s20_not_found = cross_check(s20_resolved, os.path.join(SCRIPT_DIR, "pv_master_list_s20.json"))

    report = "\n".join([
        format_report("s1", s1_resolved, s1_unresolved, s1_new, s1_not_found),
        format_report("s20", s20_resolved, s20_unresolved, s20_new, s20_not_found),
    ])
    print(report)

    out_path = args.out or os.path.join(
        SCRIPT_DIR, f"bluesky_device_scan_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt")
    with open(out_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to {out_path}")


if __name__ == "__main__":
    main()
