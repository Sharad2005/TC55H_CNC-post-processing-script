# FreeCAD CAM setup

This guide configures FreeCAD CAM to generate the same restricted TC55H files as the Fusion post. The adapter targets the FreeCAD 1.1 post-processor API and was developed against FreeCAD 1.1.3.

## Install the post

Both files are required and must remain beside each other:

- `tc55h_post.py` — FreeCAD CAM adapter
- `tc55h_core.py` — shared TC55H renderer and continuation engine

1. In FreeCAD, open **Edit → Preferences → Python → Macro** and note the user macro directory.
2. Copy both files into that directory.
3. Restart FreeCAD so the post list is refreshed.
4. In the CAM Job's **Output** settings, choose `tc55h` as the post processor.

Do not rename only one file. `tc55h_post.py` loads `tc55h_core.py` from the same directory.

## Configure the CAM Job

- Use a three-axis milling/router Job in millimetres.
- Keep exactly one fixture: FreeCAD's default `G54`. It is consumed by the adapter but never written to the TC55H file.
- Use exactly one physical tool per complete file sequence.
- Disable **Split Output**. This post creates TC55H continuation files itself.
- Leave **Arguments** empty. The safety profile accepts no post arguments.
- Set operation clearance, retract, and safe heights above the stock, clamps, and toolpath.
- Do not use rotary axes, probing, tapping, cutter compensation, or controller-side tool-length compensation.
- Program the real physical spindle RPM, up to 24,000 RPM. The post writes one tenth of it; 24,000 RPM becomes `S2400`.

The post converts FreeCAD's internal feed values from millimetres per second to TC55H millimetres per minute.

## Choose the output

Use **CAM → Post Process**. Do not use the general **File → Export** command.

Select an existing, empty output directory and an exact uppercase filename:

```text
P1.TXT
```

The name must be uppercase `P`, one to four digits, and uppercase `.TXT`. The post refuses to overwrite any required file. If the job needs more than 900 controller blocks, it writes `P1.TXT`, `P2.TXT`, and later files in the same directory.

## Verify before machining

Run the validator on the complete sequence:

```sh
python3 validate_tc55h_output.py /path/to/P1.TXT /path/to/P2.TXT
```

Compare the complete path with FreeCAD simulation. For the first physical test, remove the tool, raise Z, reduce overrides, use the TC55H syntax checker and single-block mode, and keep the emergency stop within reach.

Continuation files are manually selected and started in numeric order. Do not jog, home, reset work zero, or move the machine between files.

## Supported FreeCAD path commands

The adapter accepts ordinary rapid and linear motion, XY I/J or radius arcs, spindle start/stop, dwell, pause, and `G81`/`G82`/`G83` drilling cycles. Helical and non-XY arcs are converted to linear moves. Coolant commands are silently omitted.

Unsafe or unsupported commands stop posting with an error. These include multiple tools, non-default fixtures, inch or incremental mode, rotary motion, compensation, homing/machine-coordinate moves, optional stops, tapping, probing, and unsupported canned cycles.

## Current verification boundary

Automated tests exercise the adapter and shared renderer. FreeCAD also loaded the installed post and generated a real 169-block CAM Job file that passed the standalone validator and the Fusion-format comparison. The output has not yet been physically run on the target TC55H. Treat the first FreeCAD machine run as a commissioning program even though it follows the same controller contract as the machine-tested Fusion output.

FreeCAD references:

- [FreeCAD CAM Post documentation](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/CAM_Post.md)
- [FreeCAD 1.1.3 post-processor base class](https://github.com/FreeCAD/FreeCAD/blob/1.1.3/src/Mod/CAM/Path/Post/Processor.py)
- [FreeCAD releases](https://github.com/FreeCAD/FreeCAD/releases)
