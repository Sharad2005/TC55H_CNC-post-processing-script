# TC55H V4.005 output contract

This is the controller-facing contract used by `tc55h.cps`. It is intentionally independent of Fusion so a future CAM post can produce the same output.

## Program envelope

- Filename and Fusion program name: `P` followed by 1–4 digits, with `.TXT` extension.
- Encoding: ASCII.
- Maximum length: 999 nonempty blocks, including startup and ending blocks.
- Blocks are consecutively numbered `N1` through `N999` without padding.
- No spaces, blank lines, comments, percent signs, or unnumbered text are permitted.
- Coordinates are absolute millimetres. Work zero is established on the controller.

## Supported words

- Motion: `G00`, `G01`, `G02`, `G03`.
- State and timing: `G04`, `G90`.
- Position: `X`, `Y`, `Z`; maximum three decimal places.
- XY arc centres: relative `I` and `J`; maximum three decimal places.
- Dwell: `K` in seconds, from `0.001` to `99999.999`.
- Feed: `F` in millimetres per minute, rounded to a whole number.
- Spindle: `M03`, `M04`, `M05` and `S`.
- Program control: `M00`, `M02`.

XY arcs use incremental I/J centre offsets even though endpoint coordinates are absolute. Full circles contain I/J without an endpoint. Helical and non-XY arcs are linearized by the CAM post.

## Spindle contract

Fusion contains physical spindle RPM. The emitted TC55H command is:

`S = round(physical RPM / 10)`

The physical range is greater than zero through 24,000 RPM, producing `S1` through `S2400`. The TC55H panel spindle maximum must remain set to `2400`.

## Deliberately unsupported

The post must reject multiple tools, rotary motion, multiple setup origins, tilted workplanes, controller work offsets, cutter compensation, optional blocks, and manual passthrough commands. Coolant requests are silently omitted until a verified `M51`–`M66` GPIO mapping is added.

No program may contain generic Grbl unit, plane, retract, homing, tool-change, coolant, or ending codes.

