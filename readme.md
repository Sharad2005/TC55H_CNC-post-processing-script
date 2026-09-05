# TC55H post processor for Autodesk Fusion 360

An Autodesk Fusion 360 post processor for a Shidai Chaoqun CM45L using a TopCNC TC55H controller. It produces a deliberately small, controller-specific G-code dialect and splits programs longer than 900 blocks into manually resumed files.

> **Release status: v0.1.0 — initial Fusion 360 release.** Core XYZ posting, controller import, execution, direction, and distance were tested on the target machine. Automated formatting, scaling, and continuation tests pass. Formal arc, drilling, exact-900-block, and manual continuation acceptance remain open, so do not use this release for unattended machining.

## Target configuration

- Controller hardware: `2016K_TC55H(B)_V2.0` / `2016KTC55H(T)_V1.0`
- Controller software: `TC55HV4005Z00000` (V4.005)
- Machine mode: three-axis XYZ milling/router operation
- Units: millimetres and millimetres per minute
- One physical tool per generated sequence
- Work zero established manually on the controller
- Physical spindle range: greater than 0 through 24,000 RPM
- TC55H panel spindle maximum: `2400`
- Emitted spindle command: physical RPM divided by 10

Compatibility with other TC55H revisions or machine wiring is not assumed.

## What it does

- Emits only numbered executable blocks with exactly one ASCII space between words.
- Supports absolute rapid, linear, and XY circular motion.
- Linearizes helical and non-XY circular motion.
- Expands supported drilling cycles into basic motion and dwell blocks.
- Rejects multiple tools, rotary motion, work offsets, cutter compensation, optional sections, probing, tapping, and passthrough commands.
- Omits coolant commands until the machine's GPIO mapping is verified.
- Scales Fusion spindle values such as `24000 RPM` to TC55H `S2400`.
- Creates consecutive `P1.TXT`, `P2.TXT`, and later files when a job exceeds the 900-block operational limit.
- Includes a separate validator for individual programs and continuation handoffs.

## Repository layout

| Path | Purpose |
| --- | --- |
| `tc55h.cps` | Fusion 360 post processor |
| `TC55H_OUTPUT_SPEC.md` | Draft CAM-independent, ISA-style output specification |
| `validate_tc55h_output.py` | Static validator for one file or an ordered sequence |
| `SHA256SUMS` | Release checksums for the post and validator |
| `tests/` | JavaScript post logic tests and Python validator tests |
| `docs/FUSION_SETUP.md` | Fusion machine and NC Program configuration |
| `docs/MACHINE_TEST_CHECKLIST.md` | Staged physical-machine acceptance procedure |
| `docs/VALIDATION_STATUS.md` | Current evidence and freeze gate |
| `docs/RELEASE_NOTES_v0.1.0.md` | Scope, evidence, and known limitations of the first release |
| `report-source.md` | Controller research dossier and source ledger |

## Install in Fusion

1. Copy `tc55h.cps` into the personal Fusion post library. On macOS the usual folder is:

   ```text
   ~/Library/Application Support/Autodesk/Fusion 360 CAM/Posts/
   ```

2. Create a three-axis milling machine definition and select `TopCNC TC55H (CM45L, XYZ, continuation files)` as its post.
3. Read [the complete Fusion setup guide](docs/FUSION_SETUP.md) before posting.

## Post a program

Use an uppercase `P` followed by one to four digits for both **Name/number** and **File name**, for example `P1`. Choose an empty, dedicated output folder. Existing continuation files are never overwritten.

For a 24,000 RPM tool, the beginning of a typical file is:

```text
N1 G90 M03 S2400
N2 G00 Z5
N3 X0 Y0
```

The initial Z-only rapid is intentional: the post reaches Fusion's clearance Z before its first horizontal move.

Each generated file contains at most 900 blocks. Although the controller documentation states a 999-line capacity, the target V4.005 unit became unresponsive with a near-limit program. The post therefore keeps a 99-block safety margin. If continuation files are generated, load and start them manually in numeric order without changing work zero or machine position between files.

## Validate generated output

Python 3.10 or later is recommended. Validate one file:

```sh
python3 validate_tc55h_output.py /path/to/P1.TXT
```

Validate a continuation sequence in execution order:

```sh
python3 validate_tc55h_output.py /path/to/P1.TXT /path/to/P2.TXT /path/to/P3.TXT
```

Validation checks the file names, ASCII formatting, permitted words, block numbering, 900-block operational limit, spindle-command range, endings, consecutive filenames, and continuation position/state restoration. It does not prove that a toolpath, work offset, feed, fixture, or machine setup is safe.

## Run the automated tests

No external packages are required:

```sh
node tests/test_tc55h_cps.js
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Before running on the CNC

Follow [the machine test checklist](docs/MACHINE_TEST_CHECKLIST.md). At minimum: inspect and simulate the output, run the TC55H syntax check, remove the tool for initial tests, verify spindle start/stop and direction, use single-block mode, keep Z raised, and be ready to stop the machine. Actual 0–10 V accuracy is a machine electrical commissioning issue; the post guarantees only the emitted `S` command.

## Porting to another CAM

The post is split conceptually into a CAM adapter, a controller-independent event stream, and a TC55H renderer/partitioner. A FreeCAD Path or other CAM implementation should follow [the draft output specification](TC55H_OUTPUT_SPEC.md), not translate Fusion callback names directly.

The specification remains **Draft 0.2** until the remaining controller tests are recorded. Once the acceptance evidence is complete, a reviewed revision can be frozen as the interoperability baseline for the planned free-CAM implementation.

Current progress and the exact freeze gate are tracked in [validation status](docs/VALIDATION_STATUS.md).

## Licensing and third-party material

No project-wide open-source license has been selected yet. Public use and contribution terms must be chosen before the first release. See [NOTICE.md](NOTICE.md) for Autodesk attribution, trademarks, third-party documents, and the current licensing boundary.

Autodesk Fusion is a trademark of Autodesk, Inc. TopCNC, TC55H, CM45L, and Shidai Chaoqun names belong to their respective owners. This project is independent and is not endorsed by those companies.
