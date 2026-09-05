# Validation status

**Overall status:** v0.1.0 initial Fusion release — core XYZ machine-tested; extended acceptance in progress

**Specification:** Draft 0.2 — not frozen

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
| Analog spindle voltage accuracy | Deferred, external | TC55H/VFD electrical loading is separate from post output; `S` scaling remains unchanged |
| Arcs, drilling, and dwell | Pending | Requires target-machine execution |
| Manual continuation | Pending | Requires consecutive-file execution without repositioning |
| Material cut | Pending | Final staged acceptance step |

## Freeze gate

Do not change the specification status to Frozen until:

1. every mandatory section of `MACHINE_TEST_CHECKLIST.md` has evidence;
2. any observed difference is reflected in code, specification, and a regression test;
3. the complete automated suite passes from a clean checkout;
4. the final candidate is reposted and retested rather than relying on output from an older file; and
5. the validated commit is tagged with a release version.

Release `v0.1.0` covers Autodesk Fusion 360 only. The next implementation will target one common free CAM system after the interface specification is frozen; it must implement the controller contract rather than copy Fusion-specific callbacks.
