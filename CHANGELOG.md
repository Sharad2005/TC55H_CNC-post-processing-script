# Changelog

All notable project changes are recorded here.

## [1.0.0] - 2026-09-05

### Added

- FreeCAD CAM 1.1 adapter in `tc55h_post.py`.
- CAM-independent Python event model, renderer, spindle scaler, arc linearizer, and 900-block continuation partitioner in `tc55h_core.py`.
- FreeCAD installation and Job configuration guide.
- Automated tests for FreeCAD command translation, feed conversion, arcs, drilling, output writing, collision handling, and the shared controller core.

### Changed

- Documented Fusion and FreeCAD as two implementations of the same TC55H output contract.
- Promoted the controller interface document to the v1.0 interoperability baseline while retaining explicit machine-acceptance gaps.
- Prepared the repository as the maintainer's dual-CAM community handoff release.

### Verification boundary

- Fusion output was executed successfully on the target TC55H V4.005 machine.
- FreeCAD support is software-validated against the FreeCAD 1.1 API and requires its first target-machine acceptance run.
- A real FreeCAD CAM Job produced a 169-block output that passed the standalone validator and matched the Fusion controller-language format.

## [0.1.0] - 2026-09-05

### Added

- Three-axis Autodesk Fusion 360 post for the TC55H V4.005 profile.
- Exact single-space, numbered controller output.
- 10:1 physical-RPM to spindle-command scaling.
- Multi-file continuation with safe-Z handoff and manual restart state restoration.
- Standalone output and continuation validator.
- Automated JavaScript and Python regression tests.
- Fusion setup, machine acceptance, release notes, and draft CAM-independent interface documentation.

### Fixed

- Prevented the partitioner from treating an initial spindle event with no established XYZ position as a continuation boundary.
- Reduced the generated-file limit from the documented 999 lines to a conservative 900 blocks after the target controller became unresponsive in AUTO near the documented limit.
- Forced the first section to reach Fusion's clearance Z before its initial XY rapid.

### Machine evidence

- Confirmed that Fusion loads the post and generates controller files.
- Confirmed controller import and execution of generated TC55H G-code on software `TC55HV4005Z00000`.
- Confirmed X, Y, and Z commanded distances and coordinate directions on the target 6040 router.
- Confirmed spindle start/stop command response. Analog voltage accuracy is a separate machine electrical issue and is not corrected in the post.

### Known validation gaps

- Formal partial/full-circle, dwell, drilling, exact-900-block, manual continuation, and controlled material-cut acceptance.
- Selection of a project license after third-party rights are confirmed.
