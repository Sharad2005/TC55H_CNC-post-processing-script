# CM45L / TopCNC TC55H Technical Dossier

Audience: Owner/operator preparing for later programming, setup, diagnosis, or retrofit work

Research date: 4 September 2026

Scope: Beijing Shidai Chaoqun CM45L controller family and its TopCNC TC55H hardware/firmware lineage, installed on the tested generic 6040 XYZ CNC router.

## Direct answer

The available evidence does not identify a complete CNC machine named "Shidai Chaoqun CM45L." CM45L is a 1-4 axis standalone G-code motion-controller family made/sold by Beijing Shidai Chaoqun Electric Technology Co., Ltd. The suffix normally identifies axis count: CM45L-10 (1), -20 (2), -30 (3), and -40 (4).

The OEM relationship is unusually well supported: Shidai Chaoqun's official download named "CM45L series smart controller 1.1" is internally titled "2016 TC55H Manual V1.1," and a reseller's CM45L English manual begins by calling the controller TC55H. Its panel, terminals, specifications, menus, and command set align with TopCNC TC55H. Treat CM45L as a Shidai-branded/OEM TC55H-family controller, while still checking the physical suffix and version screen before applying a pinout or program.

Nothing found establishes the host machine's travel, spindle power, VFD, ballscrew pitch, motors/drives, coolant, lubrication, mass, mains wiring, or mechanical limits. Those are machine-builder facts, not CM45L/TC55H controller facts.

## Authoritative baseline and revisions

The best operational baseline is the official TopCNC/DPK Chinese `TC55H Series Motion Controller Manual V1.2`, published by Shandong DPK R&D Technology Co., Ltd. Its PDF was created in 2017 and modified in 2022. For CM45L branding and the relationship itself, the strongest source is Shidai Chaoqun's official 51-page `CM45L Series Smart Controller 1.1` download, whose embedded title identifies it as the 2016 TC55H V1.1 manual.

Do not mix revisions blindly:

- V1.2: 400 kHz peak pulse rate; 24/21/18 m/min controller limits at 0.001 mm pulse equivalent; 99 files and 999 lines/file; I/J full-circle arcs; G26-G28; G60/G64; G74.
- V1.1 CM45L: broadly the same 400/350/300 kHz architecture, but it states 1,000 maximum lines in one section and 799 in another. It omits G27/G28 from its command table and has a different documented multi-axis boot-homing order.
- Older English TC55H manual: 150 kHz and 9 m/min, usually 99 programs/1,000 lines (some mirrors display 100/5,000), R-form arcs only, and a smaller command set. It is an older generation, not a safe source for the newer limits.
- The controller manual itself warns that software/hardware versions vary by batch and the on-controller function prevails.

## What the controller is

- Standalone, panel-mounted motion controller using differential 5 V pulse-and-direction outputs to external stepper or servo drives.
- 1-4 feed axes named X, Y, Z, C. All configured axes can interpolate linearly; circular interpolation is only in the XY plane.
- 32-bit CPU and 2 ms interpolation cycle on the newer 2016/V1.2 generation.
- Newer published pulse limits: 400 kHz single-axis linear, 350 kHz four-axis linear, 300 kHz circular.
- At 0.001 mm pulse equivalent, published controller-command limits are 24 m/min single-axis, 21 m/min four-axis linear, and 18 m/min circular. These do not guarantee that the physical machine can safely achieve them.
- 3.5-inch 320 x 240 color LCD, Chinese/English UI, panel MPG at 0.001/0.01/0.1 units, 16 inputs, 8 outputs, USB import, and one 0-10 V analog spindle command.
- Coordinates and part count survive power loss. Do not assume spindle command, parameters, or programs have the same persistence behavior beyond what the manual states.

## Electrical and wiring model

Axis terminals are differential pairs: `Xp+/Xp-` and `Xd+/Xd-`, repeated as Y, Z, and C. Connect them to the drive's `PUL+/PUL-` and `DIR+ (or SIGN+)/DIR-` inputs.

The controller has two isolated 24 V domains:

- System `24V/0V`: display, keys, axis command generation, USB import, and analog spindle output.
- I/O `V/G`: 16 digital inputs and 8 digital outputs.

The official manuals recommend two isolated 24 V supplies for noise immunity and emphatically require the two-supply arrangement when the analog spindle output is used. A shared/simplified arrangement is shown only for few inputs and light loads.

Inputs 01-16 become active when I/O ground (`G`, 0 V) is connected through a switch/sensor to an input. They can be mapped to E-stop, alarm, positive/negative limits, home switches, external Start/Pause, feed override, external jog directions, external axis-home triggers, and program-zero. The input monitor requires a signal lasting more than 2 ms because of filtering. Wire safety inputs fail-safe normally-closed unless the actual machine safety design requires otherwise.

Outputs 01-08 are sinking/active-low outputs: a relay, solenoid, or lamp is placed between I/O `+24 V (V)` and the chosen output. M03/M04 and M51-M66 are mapped in the I/O settings to physical output numbers. Use interposing relays where the load or drive interface requires them; the TC55H-specific manuals do not establish a safe universal output-current rating.

Analog spindle terminals are `+VO` (0-10 V positive) and `-VO` (analog negative). An older English manual reverses these labels in its prose (`AGND`/`AO+`), so follow the physical rear label and the Chinese V1.1/V1.2 diagrams, not that mistranslation. The Speed/Spindle-Max parameter defines which rpm corresponds to 10 V; an `S` value scales the voltage proportionally. M03 and M04 use separately assigned digital outputs for VFD/servo forward and reverse.

Never hot-plug controller connectors. Separate high-current/VFD wiring from signal wiring, minimize crossings, use suitable conductor size, and do not short the 24 V supply to chassis/earth. VFD and welding-machine EMI are specifically relevant to this controller family.

## Operator workflow

The seven main areas are Auto, Manual, Program, Parameter, I/O, USB, and Home.

Manual mode:

- Select X/Y/Z/C, then use Left/Right for direction.
- Toggle manual high/low speed; the values come from Speed parameters.
- Incremental jog uses Control/Jog-Increment and Speed/Point-Speed.
- MPG selects 0.001, 0.01, or 0.1 unit increments.
- Program-zero moves all axes together at maximum configured speed to coordinate zero; it is not the same as machine homing.
- Long-pressing an axis key resets that displayed coordinate to its configured reference value.

Auto mode always runs the last opened program. Single-block mode executes one line for each Start press. Pause stops and later resumes with Start. Terminate stops execution and returns to the first line.

Program management supports create, edit, read/open, syntax check, save, and delete. Internal program names are 1-4 digits. In V1.2 the limit is 99 files and 999 lines/file. A saved same-name file overwrites; a USB import whose internal name already exists is rejected.

Parameter edits require login. The documented factory user password is `123456`, but it may have been changed. The manufacturer password is not provided. Factory Values restores all parameters and is explicitly marked "use cautiously." No manual documents parameter export/backup: photograph or transcribe every Control, Speed, I/O, output-map, and version screen before changing anything.

## Homing and coordinate behavior

Each axis has a reference coordinate, electronic-gear numerator/denominator, backlash compensation, boot-home enable, and home direction/input mapping. Homing approaches at Home-High, trips the home switch, then uses Home-Low according to the configured pass/not-pass-switch mode.

If boot homing is enabled on all axes, V1.2 says the sequence is X, Y, Z, C; CM45L V1.1 says X, Y, C, Z. This conflict must be resolved from the actual firmware and machine clearance before enabling automatic boot homing.

`G74 X_ Y_ Z_ C_` homes the named axes sequentially and applies the following reference coordinates. `G92` redefines the displayed/current coordinate; it is not a conventional multi-offset system. No G54-G59 work offsets are documented.

Electronic gear is:

`numerator / denominator = pulses per motor revolution / travel per motor revolution in micrometres`

Include mechanical reduction. Example from the manual: 5,000 pulses/rev, 6 mm pitch, 1:1 gives `5/6` after reduction. Verify actual driver microstep/electronic gearing and ballscrew pitch before changing this; a wrong value directly causes distance error.

## Programming dialect

This is a small proprietary G-code subset, not full Fanuc/LinuxCNC/Mach3 G-code.

Supported in V1.2:

- Motion: G00 rapid; G01 linear; G02/G03 clockwise/counter-clockwise XY arc.
- Arc forms: endpoint plus R, or endpoint plus incremental I/J center offsets. R does not support a full circle; I/J does. Positive R selects less than 180 degrees, negative R greater than 180 degrees.
- Modes: G90 absolute; G91 incremental; G60 exact-path (default); G64 continuous-path. G60/G64 must occupy their own line.
- Timing/control: G04 K(seconds); G25 unconditional jump; G26 counted loop; G27 jump when selected input is active; G28 inverse-condition jump.
- Subprograms: G20 call `Nname.repeats`; G22 begin; G24 end. Repeat count is 1-999; nested subprogram calls are not supported.
- Coordinates/home: G74 machine-home; G92 set current coordinate.
- M codes: M00 pause/wait for Start; M02 stop/end; M03/M04 spindle forward/reverse; M05 stop; M47 clear part count; M48 increment part count; M51-M66 mapped output actions.

Every block needs an N line number; blank lines and comments are not allowed; up to four M functions may appear in a block. Modal words carry until changed. The V1.2 manual contains two editing mistakes: the detailed G26 syntax line says G25 although its heading/table/example say G26, and the inverse conditional-jump section is headed/formatted G27 although the table defines it as G28. Use G26/G28 as indicated by the table, but test on the real controller in single-block with motion inhibited or clear of the work.

Not documented and therefore unsafe to assume: cutter/tool compensation, canned drilling cycles, G54-G59 work offsets, tool table/change logic, spindle encoder synchronization/threading, PLC ladder logic, macros/variables, canned lathe cycles, or arc planes other than XY. Machine-builder custom firmware may add functions, but only the actual version/interface can prove that.

## USB

The later operation guide states FAT32 USB media up to 32 GB. Program files are `.TXT`/`.txt`, filename at most 9 characters (a Chinese character counts as two). Boot images are `.BMP`/`.bmp`, at most 9 characters, exactly 320 x 240, 24-bit. USB is documented for import of programs and boot images only, not export or parameter backup. Older manuals sometimes require P-prefixed program names and K-prefixed images; V1.2 accepts general short names, so actual firmware governs.

## Troubleshooting model

- No axis movement: active limit or E-stop, zero/invalid electronic-gear value, drive alarm, or pulse/direction wiring error.
- I/O does not work: missing I/O 24 V supply, wrong physical port mapping, wrong NO/NC polarity, bad wiring, or output/input hardware fault.
- Travel distance wrong: electronic gear mismatch, driver microstep/electronic gear mismatch, or step loss/stall from excessive resistance, insufficient motor torque, or excessive acceleration.
- Spindle speed wrong: incorrect 10 V maximum-rpm parameter, analog polarity/reference wiring, failure to use isolated supplies, VFD input scaling, or EMI.
- There is no authoritative TC55H alarm-number catalog in the located documentation.

## Required identification before later work

Obtain clear photos of:

1. Controller front, exact suffix, and Version screen (software and hardware versions).
2. Rear terminal label and every occupied terminal block.
3. Complete machine nameplate (the host machine, not only the controller).
4. Electrical cabinet overview and close-ups of each stepper/servo drive, power supply, VFD/spindle drive, relay, and safety device.
5. Axis home/limit switches, motor labels, spindle label, and any builder wiring diagram.
6. Every Parameter and I/O page before edits.

Until these are captured, do not restore factory values, change electronic gearing, enable boot homing, swap +VO/-VO, or run an unverified program at normal speed.

## Material limitations

Searches in English and Chinese found the controller family, not a complete CM45L CNC machine. Reseller listings and videos were used only to corroborate labeling/workflow; they cannot establish the user's machine mechanics. No OEM contract explicitly states "CM45L equals TC55H," but the manufacturer-hosted CM45L download's internal TC55H title, combined with near-identical hardware/manual content, makes the shared lineage high confidence. Exact electrical interchangeability remains revision-specific.

## Claim-to-source ledger

1. `TC55H Series Motion Controller Manual V1.2`, Shandong DPK R&D Technology Co., Ltd.; PDF created 2017-10-14, modified 2022-03-30; official file: https://www.dpkcy.com/uploads/soft/20220726/1658820994.pdf. Primary source for current architecture, wiring, menus, parameters, I/O, programming, and revision warning.
2. `CM45L Series Smart Controller 1.1` / embedded title `2016 TC55H Manual V1.1`, Beijing Shidai Chaoqun Electric Technology Co., Ltd.; official download page dated 2022-06-02: https://www.sdcq-micromotor.cn/download_details/15.html. Primary evidence for CM45L branding, OEM lineage, wiring, and V1.1 behavior.
3. `TC55H Instruction Manual`, TOPCNC Automation Technology Co., Ltd.; PDF created 2015-04-16; mirror: https://cnccat.com/cnccat_photos/files/TOPCNC%20TC55H%20Instruction%20Manual.pdf. Older English generation; useful for UI translation and historical differences.
4. `TC55H Motion Controller Operation Guide`; later English commissioning guide; https://ae01.alicdn.com/kf/S6ef3b78c63854aa29098ed30a958f05f1.pdf. Source for FAT32/32 GB guidance, wiring/EMI cautions, and basic troubleshooting.
5. TopCNC Beijing download center, current index dated 2024-05-18 for TC55H: https://www.top-cnc.com/zlxzx. Confirms continuing official documentation availability.
6. TopCNC/DPK TC55H official product page: https://www.dpkcy.com/productshow.php?cid=7&id=83. Corroborates current product specifications.
7. Shidai Chaoqun official controller category: https://www.sdcq-micromotor.cn/Products_list/65.html. Identifies CM45L as a controller.
8. Auto520 CM45L family listing: https://www.auto520.net/p/g-code/. Secondary source for -10/-20/-30/-40 axis-count mapping and 24 V supply.
9. Mehatron `CM45L Instruction Manual`: https://mehatron.rs/Attachment/DownloadFile?downloadId=53. Secondary copy whose CM45L title and TC55H body corroborate the OEM/rebrand conclusion.

Research stopped after targeted searches produced duplicate copies of the same manuals and weaker reseller descriptions. Remaining unknowns require the physical unit and host-machine documentation, not more generic TC55H web sources.
