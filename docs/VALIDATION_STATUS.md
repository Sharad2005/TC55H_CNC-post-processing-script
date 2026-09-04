# Validation status

**Overall status:** Experimental — physical-machine validation pending

**Specification:** Draft 0.1 — not frozen

**Target controller software:** `TC55HV4005Z00000`

## Evidence available

| Area | Status | Evidence |
| --- | --- | --- |
| Fusion post loads | Pass | Fusion selected the custom post and started processing |
| Fusion oversized operation | Pass | User confirmed generation after the incomplete-handoff partition fix |
| Spindle scaling logic | Automated pass | 6000, 12000, 18000, and 24000 RPM plus invalid values |
| Exact single-space formatting | Automated pass | JavaScript and Python regression tests |
| Forced and natural splitting | Automated pass | Block accounting, retract, restart, and resume checks |
| Filename/block limits | Automated pass | Collision, overflow, and 999-block checks |
| Controller syntax check | Pending | Requires target TC55H |
| Raised-Z air run | Pending | Requires target machine |
| Spindle voltage/direction | Pending | Requires safe measurement on target machine |
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

The next planned implementation after a successful freeze is a post for a common free CAM system. That implementation must target the frozen controller interface rather than copy Fusion-specific event handling.
