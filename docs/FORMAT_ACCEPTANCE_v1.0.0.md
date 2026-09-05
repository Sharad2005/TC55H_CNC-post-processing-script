# FreeCAD format acceptance — v1.0.0

Test date: 2026-09-05

This record covers controller-file formatting only. It does not claim that Fusion and FreeCAD generated identical toolpaths, or that the FreeCAD path was physically executed.

## Test input and result

- Generator: FreeCAD CAM 1.1 with `tc55h_post.py` and `tc55h_core.py`
- Generated file: `P1.TXT`
- Generated blocks: 169 (`N1` through `N169`)
- Test-file SHA-256: `d282633f532b9cbc42942862d6770732bd93fd078240e72a1924e13a9d3bd535`
- Standalone validator: Pass — one file, 169 total blocks
- Startup: `N1 G90 M03 S1200`
- Ending: `N169 M05 M02`

The generated test file is not committed because production or test `P*.TXT` files are intentionally excluded from the repository.

## Fusion-format comparison

Coordinates and CAM-selected toolpath geometry were deliberately ignored. The comparison covered the serialized controller language:

| Property | Fusion output | FreeCAD output | Result |
| --- | --- | --- | --- |
| Block numbering | Consecutive `N` words | Consecutive `N1`–`N169` | Match |
| Word separator | One ASCII space | One ASCII space | Match |
| Addresses present | `N G M X Y Z I J F S` | `N G M X Y Z I J F S` | Match |
| Motion/state codes | `G00 G01 G02 G03 G90` | `G00 G01 G02 G03 G90` | Match |
| Program/spindle codes | `M02 M03 M05` | `M02 M03 M05` | Match |
| Comments/blank text | None | None | Match |
| Program ending | `M05 M02` | `M05 M02` | Match |

The available historical Fusion comparison sequence contained files generated under the former 999-line policy. It was used only to compare lexical structure and permitted words; it is not release-v1.0.0 block-limit evidence and must not be reused on the controller.

## Decision

**Format acceptance: PASS.**

The FreeCAD adapter produces the same restricted TC55H controller language as the Fusion adapter and conforms to TC55H Baseline 1.0 for the tested command set. It may be released as **software-validated and format-compatible**. Its physical-machine status remains untested and must not be described as machine-accepted.
