# TC55H Fusion post v0.1.0

Release date: 2026-09-05

This is the first Autodesk Fusion 360 release of the TC55H post for the tested Shidai Chaoqun CM45L / TopCNC TC55H V4.005 XYZ controller profile.

## Included

- Metric, absolute three-axis output with a deliberately restricted TC55H instruction set.
- Exact single-space formatting and sequential `N` block numbers.
- A 900-block operational limit per file.
- Automatic `P1.TXT`, `P2.TXT`, and later continuation generation, including retract and resume state.
- Clearance-Z-first startup before the initial XY rapid.
- Physical spindle RPM divided by 10 at the TC55H output boundary.
- XY I/J arcs, linearization of unsupported arcs, supported drilling expansion, and dwell output.
- Strict rejection of unsupported tools, work offsets, rotary motion, compensation, optional sections, probing, tapping, and passthrough commands.
- A standalone output/continuation validator and automated regression tests.

## Machine evidence

- Fusion loaded the post and generated TC55H files.
- The target controller imported and executed generated G-code.
- X, Y, and Z commanded distances and coordinate directions were verified.
- The target controller accepted spindle start, speed, and stop commands.
- A near-999-line program caused the target controller UI to become unresponsive; the release therefore limits generated files to 900 blocks.

## Known limitations

- Fusion 360 is the only CAM supported by this release.
- One physical tool and one setup origin are allowed per generated sequence.
- Continuation files must be selected and started manually without jogging, homing, or resetting work zero between files.
- Formal machine acceptance for arcs, drilling, dwell, exact-900-block files, manual continuation, and controlled material cutting remains open.
- Loaded 0–10 V accuracy is a machine electrical issue and is not compensated in the post. The software mapping remains `physical RPM / 10`.
- Coolant, probing, tapping, C-axis motion, automatic tool changes, and controller work-offset selection are unsupported.
- No project-wide open-source license has yet been selected; see `NOTICE.md`.

## Install and verify

1. Copy `tc55h.cps` into the Fusion personal post library and refresh or restart Fusion.
2. Optionally verify the downloaded post and validator against `SHA256SUMS`.
3. Follow `docs/FUSION_SETUP.md` and use an empty output directory.
4. Simulate the entire operation selection in Fusion.
5. Run `validate_tc55h_output.py` on every generated file in sequence.
6. Follow `docs/MACHINE_TEST_CHECKLIST.md`, beginning with a raised-Z, tool-free, single-block test.

The CAM-independent controller specification remains Draft 0.2. It will be frozen only after the remaining acceptance evidence is recorded, then used as the basis for a separate free-CAM implementation.
