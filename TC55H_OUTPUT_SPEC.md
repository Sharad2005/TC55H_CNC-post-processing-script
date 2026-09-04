# TC55H CAM Post Interface Specification

**Document status:** Draft 0.1 — developing and not frozen

**Target:** TC55H software `TC55HV4005Z00000` (V4.005), XYZ configuration

**Purpose:** CAM-independent contract for producing the same controller files as `tc55h.cps`

This is an ISA-style interface specification for post-processor authors. Here, “ISA” describes the observable program-file instruction set and continuation protocol; it is not a claim about the controller CPU architecture.

The keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** express conformance requirements. This draft remains changeable until physical-machine acceptance is complete. Passing the included validator demonstrates format conformance only, not machining safety.

## 1. Scope and conformance

A conforming CAM adapter MUST:

1. convert its CAM-specific callbacks or toolpath records into the semantic events defined below;
2. reject inputs whose meaning cannot be represented safely;
3. partition the event stream without splitting an event;
4. serialize each partition using the exact file and block grammar; and
5. preserve the executed path and required machine state across manual continuation starts.

The initial profile covers three-axis milling with one physical tool, absolute XYZ endpoints, XY arcs, spindle control, dwell, pause, and manual continuation files. C-axis operation, automatic tool change, coolant GPIO, probing, tapping, work-offset selection, and controller-side compensation are outside this profile.

## 2. Semantic input model

The CAM-specific layer SHOULD produce these controller-independent events:

| Event | Required information |
| --- | --- |
| Spindle start | Physical RPM and clockwise/counter-clockwise direction |
| Spindle speed change | Physical RPM |
| Spindle stop | No argument |
| Rapid | Absolute XYZ endpoint; unchanged axes may be retained internally |
| Linear | Absolute XYZ endpoint and feed in mm/min |
| XY arc | Direction, absolute endpoint, relative I/J centre offset, feed, and full-circle flag |
| Dwell | Seconds |
| Pause | No argument |

Every event boundary MUST retain the resulting XYZ position, active cutting feed, spindle state, operation clearance Z, and plunge feed when available. A post MUST NOT create a continuation boundary until X, Y, Z, and clearance Z are known. If resuming below clearance, a valid positive plunge feed or previous cutting feed MUST also be known.

Helical arcs, changing-Z arcs, and arcs outside the XY plane MUST be linearized before they enter this model. A canned drilling cycle MAY be expanded into rapid, linear, and dwell events only when its semantics are completely understood. Tapping and probing MUST be rejected by this profile.

## Program envelope

- Filename: uppercase `P` followed by 1–4 digits, with uppercase `.TXT` extension.
- Jobs exceeding one controller program are emitted as consecutive numbers: `P1.TXT`, `P2.TXT`, and so on.
- Encoding: ASCII.
- Maximum length: 999 nonempty blocks per file, including continuation and ending blocks.
- The complete sequence may contain at most 99 files and may not exceed `P9999.TXT`.
- Blocks restart at `N1` in every file and remain consecutive within that file.
- Every program word is separated by exactly one ASCII space, for example `N1 G90 M03 S2400`.
- Tabs, repeated spaces, leading/trailing spaces, blank lines, comments, commas, parentheses, percent signs, and unnumbered text are prohibited.
- Coordinates are absolute millimetres. Work zero is established once on the controller and must remain unchanged throughout the sequence.

The file grammar is:

```text
file        = block, LF, { block, LF } ;
block       = sequence, SP, word, { SP, word } ;
sequence    = "N", positive-decimal-integer ;
word        = address, signed-decimal-number ;
address     = "G" | "M" | "X" | "Y" | "Z" | "I" | "J" | "K" | "F" | "S" ;
SP          = ASCII 0x20 ;
LF          = ASCII 0x0A ;
```

Readers MAY accept a final block without a trailing LF, but writers SHOULD emit one. Writers MUST NOT emit lowercase letters, tabs, CR-only endings, Unicode, blank blocks, leading/trailing spaces, or more than one space between words.

The first file MUST begin with a block containing `G90`, the requested spindle direction (`M03` or `M04`), and the scaled `S` value. The last block of every file MUST be exactly `M05 M02`.

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

### Numeric representation

- `G` and `M` codes MUST use two digits: `G00`, `G01`, `M03`.
- `N`, `F`, and `S` MUST be positive whole decimal numbers without padding.
- XYZ and I/J values MUST use at most three fractional digits and MUST NOT exceed `±99999.999`.
- K MUST be from `0.001` through `99999.999` seconds with at most three fractional digits.
- Redundant trailing fractional zeroes SHOULD be removed.
- A serializer SHOULD suppress unchanged modal motion, coordinates, feed, and spindle speed when doing so preserves unambiguous execution.

`G90` makes XYZ endpoints absolute. I/J remain relative offsets from the arc start. No unit-selection or plane-selection words are emitted; the controller and operator setup MUST already agree on millimetres and the XY arc plane.

## Continuation contract

- The controller does not automatically call the next file; the operator runs files in numeric order.
- A split is made only after a complete motion. A nearby clearance-height endpoint is preferred; a forced split may occur at a completed cutting endpoint.
- An intermediate file keeps the spindle running while retracting Z to the operation clearance height, then ends with `M05 M02`.
- The next file restores `G90`, spindle direction and scaled speed, rapids to the saved X/Y at clearance Z, and feeds to the saved Z using the Fusion plunge feed.
- If the split endpoint is already at clearance height, the redundant retract and descent are omitted.
- The next unexecuted CAM motion follows the re-entry; the previously completed motion is not repeated.
- Existing continuation filenames cause posting to stop instead of overwriting them.

### Partition algorithm

For each output file, the implementation MUST reserve enough blocks for that file's opening and ending before selecting its final event. It SHOULD choose the most recent valid clearance-height boundary within the preceding 100 events. Otherwise, it MAY choose the last valid complete-event boundary that fits.

An intermediate ending is:

```text
N... G00 Z<clearance-or-higher>
N... M05 M02
```

The retract is omitted when the saved Z is already at or above clearance. The spindle remains active during the retract and is stopped only in the final block.

A continuation opening is:

```text
N1 G90 M03 S<scaled-speed>
N2 G00 X<saved-X> Y<saved-Y>
N3 G01 Z<saved-Z> F<plunge-feed>
```

Direction may be `M04`; spindle words are omitted if the saved spindle state was stopped. The Z descent is omitted when the split occurred at clearance height. Modal state MUST be treated as unknown at each new file, so the first resumed machining event MUST explicitly supply the required motion mode and feed. The previously completed event MUST NOT be emitted again.

## Spindle contract

Fusion contains physical spindle RPM. The emitted TC55H command is:

`S = round(physical RPM / 10)`

The physical range is greater than zero through 24,000 RPM, producing at most `S2400`. The TC55H panel spindle maximum must remain set to `2400`.

The division and rounding MUST be applied once at the output boundary for both initial spindle start and later speed changes. CAM data and intermediate events retain physical RPM. Requests at or below zero or above 24,000 RPM MUST stop generation.

## Deliberately unsupported

The post must reject multiple tools, rotary motion, multiple setup origins, tilted workplanes, controller work offsets, cutter compensation, optional blocks, and manual passthrough commands. Coolant requests are silently omitted until a verified `M51`–`M66` GPIO mapping is added.

No program may contain generic Grbl unit, plane, retract, homing, tool-change, coolant, or ending codes.

Specifically prohibited output includes `G17`–`G21`, `G28`, `G43`, `G53`, `G54`–`G59`, `G74`, `G93`–`G95`, `M06`, `M08`, `M09`, and `M30`.

## Error and overwrite behavior

A conforming generator MUST fail before producing continuation files when:

- the requested base name does not match `P` plus 1–4 digits;
- the sequence would contain more than 99 files;
- the final number would exceed `P9999.TXT`;
- any required continuation filename already exists;
- a section changes tool, setup origin, or supported workplane;
- no safe and resumable split boundary fits; or
- any required value is invalid or unsupported.

The base output file may be managed by the CAM application's normal overwrite confirmation. Continuation files MUST NOT be silently replaced.

## Conformance evidence required before freezing

The draft may be frozen only after recording successful results for:

- rapid and linear positioning, feed changes, and pauses;
- clockwise/counter-clockwise spindle direction and stop behavior;
- physical spindle tests at 6000, 12000, 18000, and 24000 RPM;
- partial arcs and full circles in both directions;
- supported drilling expansion and dwell timing;
- 999-block acceptance and 1000-block splitting;
- forced below-clearance and natural clearance-height continuations;
- manual execution of at least two consecutive files without coordinate drift;
- rejection of invalid speed, multiple tools, rotary paths, and unsupported commands; and
- comparison of the reconstructed multi-file path with the originating CAM simulation.

Until that evidence is complete, implementations MUST identify themselves as experimental and SHOULD expose the specification revision they target.

## Open items for a later revision

- Verified controller behavior for every permitted word on the target hardware/firmware.
- Exact CM45L travel, acceleration, rapid, and feed limits.
- Confirmed rounding and coordinate precision behavior at controller boundaries.
- Safe and electrically verified `M51`–`M66` coolant/GPIO mapping.
- C-axis orientation, units, gearing, limits, and indexed versus simultaneous operation.
- Results from a second CAM implementation and cross-CAM path comparison.

Changes to any file grammar, word meaning, spindle scaling, or continuation invariant are breaking changes until a compatibility policy is defined.
