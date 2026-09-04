# Contributing

This project controls real machinery. Small formatting changes can create unsafe motion, so every behavioral change needs evidence.

## Before proposing a change

1. Open an issue describing the controller hardware/software version, CAM, intended behavior, and observed output.
2. Do not generalize behavior seen on another TC55H revision without identifying that revision.
3. Preserve the separation between CAM event capture and controller rendering.
4. Add a regression test for every fixed defect or new rule.
5. Run both test suites and validate representative generated files.
6. State whether the change was syntax-tested, air-cut, or material-tested on real hardware.

Never commit generated `P*.TXT` production files, personal machine parameters, credentials, `.DS_Store`, cache folders, or third-party manuals/source files without clear redistribution permission.

Changes to the draft interface specification require a rationale and compatibility impact. Do not mark it frozen until the physical acceptance checklist has passed and the supporting results are committed.
