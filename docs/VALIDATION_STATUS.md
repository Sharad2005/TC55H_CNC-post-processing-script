# Validation status

**Overall status:** v1.0.0 dual-CAM handoff — Fusion machine-tested; FreeCAD software-tested

**Specification:** Baseline 1.0 — frozen output contract

**Target controller software:** `TC55HV4005Z00000`

## Evidence available

| Area | Status | Evidence |
| --- | --- | --- |
| Fusion post loads | Pass | Fusion selected the custom post and started processing |
| Fusion oversized operation | Pass | User confirmed generation after the incomplete-handoff partition fix |
| Controller import and execution | Pass | User-reported successful execution on the target TC55H V4.005 unit |
| XYZ direction and distance | Pass | All three axes verified; X direction corrected at the X-axis driver's `P002`, not in the post |
| Spindle scaling logic | Automated pass | 6000, 12000, 18000, and 24000 RPM plus invalid values |
| First-move clearance ordering | Automated pass | Initial Z-only rapid precedes the first XY rapid |
| Exact single-space formatting | Automated pass | JavaScript and Python regression tests |
| Forced and natural splitting | Automated pass | Block accounting, retract, restart, and resume checks |
| Filename/block limits | Automated pass | Collision, overflow, and 900-block operational-cap checks |
| Near-documented-limit program | Failed | Target controller became unresponsive in AUTO with a near-999-line program; operational cap reduced to 900 |
| Core controller syntax/motion | Pass | Generated program accepted and executed; XYZ directions and distances confirmed |
| FreeCAD 1.1 adapter | Automated pass | Commands, units, spindle, arcs, drilling, errors, file writing, and collision handling |
| Shared FreeCAD output core | Automated pass | Formatting, scaling, linearization, 900-block partition, retract, restart, and filenames |
| FreeCAD GUI/runtime | Not run locally | Installed application command-line engine reports an incompatible Qt processor build on the development Mac |
| FreeCAD output on target machine | Pending | Requires staged tool-free execution and comparison with FreeCAD simulation |
| Analog spindle voltage accuracy | Deferred, external | TC55H/VFD electrical loading is separate from post output; `S` scaling remains unchanged |
| Arcs, drilling, and dwell | Pending | Requires target-machine execution |
| Manual continuation | Pending | Requires consecutive-file execution without repositioning |
| Material cut | Pending | Final staged acceptance step |

## Adapter acceptance gate

Do not describe the FreeCAD adapter as machine-accepted until:

1. every mandatory section of `MACHINE_TEST_CHECKLIST.md` has evidence;
2. any observed difference is reflected in code, specification, and a regression test;
3. the complete automated suite passes from a clean checkout;
4. the final candidate is reposted and retested rather than relying on output from an older file; and
5. the validated commit and generated files are recorded.

Release `v1.0.0` contains both Fusion 360 and FreeCAD CAM implementations. Baseline 1.0 freezes their controller-facing contract; future incompatible changes require a new specification revision.
