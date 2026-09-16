#!/usr/bin/env python3
"""
Device-type groupings for pv_master_list_{s1,s20}.json's "group" field.

Originally lived in pv_logger_gui.py (for the Start-new-experiment
checklist, so related groups - e.g. the 8 different furnace groups,
scattered across the alphabet under names like "FZHANG COLD SINTER
FURNACE"/"RF Furnace"/"SUTER-BASIL FURNACE" - land together instead of a
flat alphabetical list of ~80 groups) and moved here (2026-09-16) so
pv_logger.py's headless CLI/systemd logger can reuse the same category
data for CSV column ordering without gaining a PyQt5 dependency - this
module imports nothing beyond the standard library.

Presentation-only - doesn't touch the master list's own "group" field or
PV filtering, which still key off the group name exactly as before. A
group name not listed here (e.g. one a rename just created) falls into
the "Other" catch-all category rather than being dropped, so this
mapping can lag behind the master lists without breaking anything - just
showing up uncategorized until updated.
"""

DEVICE_CATEGORIES = [
    ("Detectors", [
        # One group per physical detector/camera (2026-09-16, per direct
        # confirmation) - each bundles that detector's armed-state,
        # frame-number, and acquisition-setting PVs (previously spread
        # across three separate groups: "Detectors (armed state)",
        # "DETECTORS frame number", and a per-detector "X Acquisition
        # Settings"), so selecting a detector for a run is one click
        # instead of three. Hydra GE1-5 are five separate groups (distinct
        # physical units), not one shared "GE" group.
        "Eiger", "Pilatus", "VarexC", "PG1", "GH1", "PG5", "SP5", "Dexela",
        "Andor", "CoolSnap", "QIMAGE2", "QIMAGE1", "Pixirad", "ASI (Medipix3)",
        "Lambda", "dic",
        "Hydra GE1", "Hydra GE2", "Hydra GE3", "Hydra GE4", "Hydra GE5",
        # Motor-position and sensor groups intentionally left as-is (not
        # camera/plugin PVs). "D2 Detector" split into C-hutch/E-hutch
        # (2026-09-16, per direct confirmation) - same "D2" name, two
        # physically distinct stages, previously conflated (the E-hutch one
        # was misleadingly named "GE/Pilatus DETECTOR"). Bare "D2 Detector"
        # (s20's ungrouped variant of the same split, 2026-09-16) added here
        # too rather than left to fall into "Other".
        "D2 Detector (C-hutch)", "D2 Detector (E-hutch)", "D2 Detector", "NF DET", "Tomo det",
        "BSE1 Detector", "BSE2 Detector", "D3 Detector", "D4-1 Detector", "D4-2 Detector",
        "GH2 Detector", "PG6 Detector", "PITEC1 Detector", "Varex Detector",
        # bluesky-sourced detector-arm/near-far-field positioning stages (2026-08-26 scan)
        "tomoB", "tomoC", "tomoD", "tomoE",
    ]),
    ("A Lens Stacks", [
        "A Lens Stack 1", "A Lens Stack 2", "A Lens Stack 3",
    ]),
    ("B Lens Stacks", [
        "L1", "L2", "RL", "CRL1", "CRL2", "lens4B", "lens5B",
    ]),
    ("C Lens Stacks", [
        "C Lens Stack 1", "C Lens Stack 2", "C Lens Stack 3", "C Lens Stack 4", "C Lens Stack 7",
    ]),
    ("D Lens Stacks", [
        "D Lens Stack 1", "D Lens Stack 2", "D Lens Stack 3", "D Lens Stack 4",
        "D Lens Stack 5", "D Lens Stack 6",
    ]),
    ("E Lens Stacks", [
        "E Lens Stack 1", "E Lens Stack 2", "E Lens Stack 3", "E Lens Stack 4",
    ]),
    ("TXM", [
        "txmE", "txm_cam", "txm_lensE", "tomoEds",
    ]),
    ("Monochromators", ["HEM", "HRM"]),
    ("B Slits", ["B Slits"]),
    ("C Slits", ["C Upstream Slits", "C Downstream Slits"]),
    ("D Slits", ["D Upstream Slits", "D Downstream Slits", "D T7 Slits"]),
    ("E Slits", ["E Upstream Slits", "E Downstream Slits"]),
    ("White Beam Slits", ["White Beam Slits"]),
    ("Scalers / Ion Chambers", [
        "C Scaler (raw channels)", "E Scaler (raw channels)", "Ion Chamber",
        "A Hutch Ion Chambers", "B Hutch Ion Chambers", "C Hutch Ion Chambers",
        "D Hutch Ion Chambers", "E Hutch Ion Chambers",
    ]),
    ("Sample Environment", [
        "PulseRay-CMU furnace", "FZHANG COLD SINTER FURNACE",
        "HASTINGS FURNACE", "IR FURNACE", "LANL RF FURNACE", "LINKAM FURNACE", "RF Furnace",
        "E PulseRay Furnace", "Linkam Furnace (old)",
        "NIST BOULDER CONNOLLY H2 CHAMBER", "LANL CHILLER", "LANL WELDER", "AM chamber setup",
        # bluesky-sourced (2026-08-26 scan)
        "amD", "rf_sam", "rf_tube",
    ]),
    ("Load Frames / Mechanical Testing", [
        "Compact loadframe", "Compact loadframe UL / DESY", "AML Psylotech muTS",
        "MTS", "MTS+RAMS1+OXYGON setup", "OWIS compression type",
        "psylotech_out",  # bluesky-sourced (2026-08-26 scan)
    ]),
    ("Sample Stages / Motors", [
        "Motors",
    ]),
    ("Sample Manipulation Systems", [
        "C HR-SMS", "C 4-Circle Diffractometer", "D-HRSMS", "E HR-SMS", "E-HRSMS", "E-HLSMS", "E HL-SMS",
        # bluesky-sourced sample positioning stages (2026-08-26 scan)
        "aeroD",
        # "hlsms" (single stray PV, 20ide2:m89) merged into E-HLSMS as
        # E_HLSMS_RotZ (2026-09-10, per direct confirmation) - it shared
        # the same 20ide2 IOC prefix and axis-naming convention as every
        # other E-HLSMS entry (RotX/RotY1-3), just hadn't been grouped in.
    ]),
    ("Sensors / Environmental", [
        "KEYENCE", "FLOW METER", "Hutch monitoring thermocouples", "THERMOCOUPLE", "TC32",
    ]),
    ("Beam / Storage Ring", [
        "Beam Position Monitor", "Storage Ring Status", "Experiment Identifiers", "Scan Parameters",
    ]),
    ("Storage Ring / Undulator", ["Storage Ring", "Undulator", "Insertion Devices"]),
    ("Lab Equipment", ["AGILENT FUNC GEN", "beeper"]),
    ("Shutters / Shields / Foils", [
        "Shields", "Shutters", "Foils. attens", "Attenuator",
        # bluesky-sourced (2026-08-26 scan)
        "attenA", "attenE", "foilA", "saxs", "saxs_pin",
    ]),
    ("Software / Misc", [
        "INITATE LOGGING", "handshake signals", "VOLTAGE SIGNAL POKHAREL_MAR18",
        "write_parfile_general.mac (misc, review before use)", "Calculation/Software", "Miscellaneous",
        "wheelE",  # per direct confirmation (2026-08-26)
    ]),
]

_CATEGORY_FOR_GROUP = {
    group: category for category, groups in DEVICE_CATEGORIES for group in groups
}

_OTHER_CATEGORY = "Other"


def _category_for_device(device):
    return _CATEGORY_FOR_GROUP.get(device, _OTHER_CATEGORY)
