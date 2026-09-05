# TC55H dual-CAM post processors v1.0.0

Release date: 2026-09-05

This is the maintainer's final dual-CAM handoff release for the Shidai Chaoqun CM45L / 6040 router with TopCNC TC55H V4.005. It includes Autodesk Fusion 360 and FreeCAD CAM 1.1 paths to the same TC55H Baseline 1.0 output contract.

## Included

- Machine-used Autodesk Fusion post: `tc55h.cps`.
- FreeCAD 1.1 post adapter: `tc55h_post.py`.
- Shared FreeCAD-side controller engine: `tc55h_core.py`.
- Exact numbered, single-space ASCII output with a 900-block maximum.
- Consecutive continuation files with safe retract and state restoration.
- Physical spindle RPM divided by 10, limited to 24,000 RPM input and `S2400` output.
- XY arcs, unsupported-arc linearization, supported drilling expansion, dwell, and strict rejection of unsafe features.
- Standalone validator, regression tests, setup guides, acceptance checklist, and Baseline 1.0 interface specification.

## Evidence

- Fusion output was imported and executed on the target TC55H V4.005 machine.
- X, Y, and Z directions and commanded distances were confirmed.
- The controller accepted the post's spindle commands; loaded analog-voltage loss remains a separate electrical issue.
- The Fusion and Python automated suites pass.
- FreeCAD adapter tests cover command translation, mm/s to mm/min conversion, spindle scaling, arcs, drilling, errors, file creation, collisions, and continuation behavior.
- A real FreeCAD CAM Job generated a 169-block `P1.TXT` file with SHA-256 `d282633f532b9cbc42942862d6770732bd93fd078240e72a1924e13a9d3bd535`.
- That file passed the standalone validator and matched the Fusion output's spacing, numbering, address set, permitted G/M codes, startup structure, and ending structure.

## Important limitations

- FreeCAD is format-compatible and software-validated, but its output has not completed a target-machine run. Begin with a tool-free, raised-Z, single-block commissioning program.
- One physical tool and one default fixture are allowed per sequence.
- Continuation files are selected and started manually without jogging, homing, or resetting work zero.
- Coolant GPIO, probing, tapping, tool changes, C-axis motion, controller offsets, and compensation are unsupported.
- Controller/VFD loaded analog-voltage accuracy is not compensated in either post.
- This repository still has no project-wide open-source license because the Fusion file derives from an Autodesk factory post whose redistribution terms require confirmation. See `NOTICE.md`.

## Install and verify

- Fusion: follow `docs/FUSION_SETUP.md`.
- FreeCAD: follow `docs/FREECAD_SETUP.md` and install both Python files together.
- Post to an empty directory using an exact uppercase name such as `P1.TXT`.
- Run `validate_tc55h_output.py` over every generated file in order.
- Simulate in the originating CAM and follow `docs/MACHINE_TEST_CHECKLIST.md`.
