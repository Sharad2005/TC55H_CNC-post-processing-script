# Changelog

All notable project changes will be recorded here. The project has no machine-validated release yet.

## Unreleased

### Added

- Three-axis Fusion post for the TC55H V4.005 profile.
- Exact single-space, numbered controller output.
- 10:1 physical-RPM to spindle-command scaling.
- Multi-file continuation with safe-Z handoff and manual restart state restoration.
- Standalone output and continuation validator.
- Automated JavaScript and Python regression tests.
- Fusion setup, machine acceptance, and draft CAM-independent interface documentation.

### Fixed

- Prevented the partitioner from treating an initial spindle event with no established XYZ position as a continuation boundary.

### Pending

- TC55H syntax-check, air-run, spindle, arc, dwell, drilling, continuation, and material-cut acceptance.
- Selection of a project license after third-party rights are confirmed.
