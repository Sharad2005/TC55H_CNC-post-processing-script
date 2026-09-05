# Physical-machine acceptance checklist

This checklist is evidence for developing the post; it is not a substitute for the machine manufacturer's safety procedure. Stop if the actual controller, wiring, axis direction, spindle behavior, or firmware differs from the documented target.

Record the date, Fusion version, `tc55h.cps` checksum/commit, controller hardware/software version, test file names, operator, and outcome for every session.

For FreeCAD tests, record the FreeCAD version plus the checksums of both `tc55h_post.py` and `tc55h_core.py`. Run the same motion, continuation, and material checks and compare against the FreeCAD simulation.

FreeCAD format acceptance was recorded on 2026-09-05: a real CAM Job generated 169 sequential blocks, passed `validate_tc55h_output.py`, and matched the Fusion controller-language structure. This reduces the remaining FreeCAD work to physical motion acceptance; it does not replace it.

## Evidence recorded for v0.1.0

On 2026-09-05 the target TC55H V4.005 machine successfully imported and executed generated output. X, Y, and Z commanded distances and coordinate directions were confirmed. X direction was corrected using the X-axis ZDM-2HA865 driver's `P002` setting; this was a machine configuration change, not a post change. The post's spindle commands were accepted, while inaccurate loaded analog voltage was classified as a separate controller/VFD electrical issue.

Unchecked items below remain the formal acceptance work for freezing the CAM-independent specification.

## 1. Before applying motion

- [ ] Photograph or record all TC55H Control, Speed, I/O, output-map, and version pages.
- [ ] Confirm hardware and software versions match the target profile.
- [ ] Confirm the TC55H spindle maximum is `2400`.
- [ ] Confirm E-stop, limit switches, drive alarms, and spindle stop work independently.
- [ ] Confirm axis directions and displayed coordinates using manual low-speed jog.
- [ ] Remove the cutting tool for the first tests.
- [ ] Remove stock and fixtures or establish generous clearance.
- [ ] Use a dedicated empty output folder and retain the original Fusion simulation.
- [ ] Run `validate_tc55h_output.py` on the entire generated sequence.
- [ ] Inspect every line and run the TC55H syntax checker on every file.

## 2. Spindle command and machine electrical test

Keep axes stationary and measure the VFD command or spindle behavior safely. The required-output column is the software contract. Voltage/RPM accuracy depends on controller and VFD wiring and is recorded separately from post conformance.

| Fusion RPM | Required output | Expected physical result | Pass |
| ---: | ---: | ---: | :---: |
| 6000 | `S600` | approximately 6000 RPM / 2.5 V | [ ] |
| 12000 | `S1200` | approximately 12000 RPM / 5 V | [ ] |
| 18000 | `S1800` | approximately 18000 RPM / 7.5 V | [ ] |
| 24000 | `S2400` | approximately 24000 RPM / 10 V | [ ] |

- [ ] `M03` produces the intended forward direction.
- [ ] `M04` is either verified safely or deliberately prohibited operationally.
- [ ] `M05` stops the spindle reliably.
- [ ] Zero, negative, and above-24,000 RPM requests fail during posting.

Measured voltage/RPM and deviations:

```text
6000:
12000:
18000:
24000:
```

A voltage or RPM deviation does not justify changing the post's fixed 10:1 mapping unless the TC55H command semantics are proven different. Diagnose controller power, analog-output loading, VFD configuration, and wiring independently.

## 3. Raised-Z motion test

- [ ] Use a short program with known positive X, Y, and Z movements.
- [ ] Set work zero with Z high enough that no tool or collet can contact the table.
- [ ] Select single-block mode and reduce feed/rapid override.
- [ ] Verify `G90`, `G00`, and `G01` directions and distances one block at a time.
- [ ] Verify modal coordinate and feed suppression does not change the intended path.
- [ ] Verify pause (`M00`) and resume behavior.
- [ ] Verify `M05 M02` leaves the controller in the expected stopped state.

## 4. Arc and dwell test

- [ ] Test a clockwise partial XY arc.
- [ ] Test a counter-clockwise partial XY arc.
- [ ] Test clockwise and counter-clockwise full circles using I/J.
- [ ] Compare endpoint, centre, direction, and shape with Fusion simulation.
- [ ] Confirm helical and changing-Z arcs were linearized.
- [ ] Verify at least two `G04 K...` dwell durations.

## 5. Drilling expansion test

- [ ] Use only a supported non-tapping, non-probing drilling operation.
- [ ] Confirm the posted rapid, plunge, dwell, retract, and clearance values match Fusion.
- [ ] Air-run the expanded cycle in single-block mode.
- [ ] Confirm tapping and probing operations stop posting with an error.

## 6. Block limit and continuation test

First use two deliberately short continuation files; do not begin with a 900-block cutting program.

- [ ] Confirm every file begins at `N1` and contains no more than 900 blocks.
- [ ] Confirm intermediate files retract Z before `M05 M02` when below clearance.
- [ ] Confirm the following file restores `G90`, direction, and scaled spindle speed.
- [ ] Confirm it rapids to saved X/Y while the machine remains at safe Z.
- [ ] Confirm it feeds back to saved Z with the intended plunge feed.
- [ ] Confirm the first new machining motion is explicit and no completed motion repeats.
- [ ] Without jogging or rezeroing, manually start the next file and compare the resumed path.
- [ ] Test a natural split at clearance and verify redundant Z descent is absent.
- [ ] Generate exactly 900 blocks in one file and confirm controller acceptance without UI lockup.
- [ ] Generate a job requiring a 901st block and confirm correct splitting.
- [ ] Confirm an existing continuation filename causes posting to fail without overwrite.

## 7. Controlled material test

Perform this only after all preceding checks pass.

- [ ] Install a suitable tool and secure sacrificial material.
- [ ] Verify tool, collet, spindle direction, work zero, clearance, feeds, speeds, and fixture clearance again.
- [ ] Use conservative override, single-block entry, and a shallow test path.
- [ ] Compare the finished dimensions and arc geometry with the programmed path.
- [ ] Record any controller rounding, pause, restart, or path-quality behavior.

## Acceptance decision

- [ ] All mandatory tests passed without unexplained behavior.
- [ ] Failures and changes were recorded as issues and regression tests.
- [ ] The draft ISA was updated to match observed controller behavior.
- [ ] A specific tested commit was tagged as the first machine-validated release.
- [ ] Only then was the ISA status changed from Draft to Frozen.

Result: `NOT TESTED / FAILED / PARTIAL / PASSED`

Notes:

```text

```
