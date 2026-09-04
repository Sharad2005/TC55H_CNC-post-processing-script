# Fusion setup

This setup targets initial three-axis testing of `tc55h.cps`. Values marked temporary affect Fusion simulation and time estimates; replace them when the physical CM45L parameters are documented.

## Install the post

Copy `tc55h.cps` into the personal Fusion post library. Restart Fusion or refresh the post library after replacing an existing copy.

Typical macOS location:

```text
~/Library/Application Support/Autodesk/Fusion 360 CAM/Posts/
```

## Machine definition

### General

- Vendor: `Shidai Chaoqun / TopCNC`
- Model: `CM45L TC55H 3-Axis`
- Description: `3-axis XYZ CNC router, TC55H V4.005, 24000 RPM spindle`

### Capabilities

- Capability: Milling only
- Automatic tool changer: Off
- Tool preload: Off
- Number of tools: 1
- Max feedrate: `5000 mm/min` temporarily
- Max block processing speed: `500`
- Rapid interpolation, TCP off: Synchronized Axes
- TCP-on behavior: unused in this three-axis profile

Replace the temporary feedrate with the lowest verified X/Y/Z machine limit. Do not infer it from the controller's theoretical maximum.

### Kinematics

For X, Y, and Z:

- Coordinate and name: matching axis letter
- Home position: `0 mm` temporarily
- Tool-change position: `0 mm` (unused)
- Rapid feedrate: `5000 mm/min` temporarily
- Max feedrate: `5000 mm/min` temporarily
- Orientation: From coordinate
- Range: Unlimited temporarily
- Resolution: Continuous
- Axis function: Machining

Do not add guessed travel limits. Change each range to Limited only after measuring or obtaining the real travel, coordinate direction, and home location. The generic kinematic tree is sufficient for posting, but it is not an accurate physical machine simulation without a model.

### Post processing and model

- Post: `TopCNC TC55H (CM45L, XYZ, continuation files)`
- Output folder: a dedicated folder that does not contain old `P*.TXT` files
- Feedrate ratio: `100%`
- Tool-change time: `0 s`
- Machine model: none until accurate geometry and component assignments exist

## CAM setup requirements

- Use millimetres.
- Align the tool with setup +Z; use the XY plane for arcs.
- Establish one setup origin that matches the work zero the operator will set on the TC55H.
- Set Fusion WCS offset to `0`; do not request G54–G59.
- Use one physical tool across all selected operations.
- Program physical spindle RPM, up to 24,000. Do not enter the divided controller value in Fusion.
- Define clearance and retract heights that are genuinely safe for stock, clamps, and fixtures.
- Define a positive plunge feed for every operation that may be split below clearance.
- Simulate the complete selection before posting.

## NC Program settings

- Use machine configuration: On
- Machine: the saved CM45L/TC55H machine
- Post: the installed TC55H post
- Cascading post: Off
- Name/number: `P` plus 1–4 digits, for example `P1`
- File name: exactly the same value, for example `P1`
- Comment: empty
- Unit: Millimetres, or Document units only if the document is metric
- Open NC file in editor: useful during testing

Leave the built-in post properties at their supplied values. In particular, keep helical moves disabled and high-feed mapping set to Preserve rapid movement.

## Continuation files

The post can split inside a single operation. It creates sequential names beginning at the requested number. `P7` may therefore produce `P7.TXT`, `P8.TXT`, and `P9.TXT`.

Before posting, move or delete obsolete files with those names from the output folder. The post refuses to overwrite continuation files. Validate and inspect every generated file, then execute them manually in numeric order without jogging, rezeroing, homing, or otherwise changing machine position between files.
