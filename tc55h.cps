/**
  TC55H post processor for Autodesk Fusion.

  Derived from the Autodesk Grbl post supplied with this project.
  Copyright (C) 2012-2026 by Autodesk, Inc.
  TC55H adaptation Copyright (C) 2026.

  Target controller:
    2016K_TC55H(B)_V2.0 / 2016KTC55H(T)_V1.0
    Software TC55HV4005Z00000
*/

description = "TopCNC TC55H (CM45L, XYZ)";
vendor = "TopCNC / Shidai Chaoqun";
vendorUrl = "https://www.topcnc.net/";
legal = "Derived from Autodesk Grbl post; Copyright (C) 2012-2026 Autodesk, Inc.";
certificationLevel = 2;
minimumRevision = 45917;

extension = "TXT";
setCodePage("ascii");

capabilities = CAPABILITY_MILLING;
unit = MM;

tolerance = spatial(0.002, MM);
minimumChordLength = spatial(0.25, MM);
minimumCircularRadius = spatial(0.01, MM);
maximumCircularRadius = spatial(1000, MM);
minimumCircularSweep = toRad(0.01);
maximumCircularSweep = toRad(360);
allowHelicalMoves = false;
allowSpiralMoves = false;
allowedCircularPlanes = 1 << PLANE_XY;

var TC55H_MAXIMUM_PROGRAM_BLOCKS = 999;
var TC55H_MAXIMUM_PHYSICAL_SPINDLE_RPM = 24000;
var TC55H_SPINDLE_COMMAND_DIVISOR = 10;

// Future coolant support belongs here. Map the required TC55H M51-M66 GPIO
// commands only after the controller I/O assignment and electrical behavior
// have been verified. Coolant is intentionally silent everywhere else.
var TC55H_COOLANT_OUTPUT_DISABLED = true;

var xyzFormat = createFormat({decimals:3, type:FORMAT_REAL});
var feedFormat = createFormat({decimals:0});
var spindleFormat = createFormat({decimals:0});
var secondsFormat = createFormat({decimals:3, type:FORMAT_REAL});
var gFormat = createFormat({prefix:"G", decimals:0, width:2, zeropad:true});
var mFormat = createFormat({prefix:"M", decimals:0, width:2, zeropad:true});

var xOutput = createOutputVariable({prefix:"X"}, xyzFormat);
var yOutput = createOutputVariable({prefix:"Y"}, xyzFormat);
var zOutput = createOutputVariable({prefix:"Z"}, xyzFormat);
var feedOutput = createOutputVariable({prefix:"F"}, feedFormat);
var iOutput = createOutputVariable({prefix:"I", control:CONTROL_FORCE}, xyzFormat);
var jOutput = createOutputVariable({prefix:"J", control:CONTROL_FORCE}, xyzFormat);

var gMotionModal = createOutputVariable({}, gFormat);

var emittedBlockCount = 0;
var spindleIsRunning = false;
var spindleDirectionClockwise;
var lastSpindleCommand;
var firstToolId;
var setupOrigin;
var setupForward;

function writeBlock() {
  var words = formatWords(arguments);
  if (!words) {
    return;
  }
  if (emittedBlockCount >= TC55H_MAXIMUM_PROGRAM_BLOCKS) {
    error(localize("TC55H program exceeds the 999-block controller limit."));
    return;
  }
  ++emittedBlockCount;
  writeWords("N" + emittedBlockCount, words);
}

function validateProgramIdentity() {
  if (!programName || !/^P[0-9]{1,4}$/.test(String(programName))) {
    error(localize("Program name must be uppercase P followed by 1 to 4 digits, for example P123."));
  }

  var expectedFilename = String(programName) + ".TXT";
  var actualFilename = FileSystem.getFilename(getOutputPath()).toUpperCase();
  if (actualFilename != expectedFilename) {
    error(localize("Output filename must match the program name and use .TXT: " + expectedFilename));
  }
}

function validateJob() {
  if (getNumberOfSections() < 1) {
    error(localize("The NC program contains no machining operations."));
    return;
  }

  var firstSection = getSection(0);
  firstToolId = firstSection.getTool().getToolId();
  setupOrigin = firstSection.workOrigin;
  setupForward = firstSection.workPlane.forward;

  for (var sectionIndex = 0; sectionIndex < getNumberOfSections(); ++sectionIndex) {
    var section = getSection(sectionIndex);
    if (section.getTool().getToolId() != firstToolId) {
      error(localize("TC55H programs must contain exactly one physical tool."));
    }
    if (section.workOffset != 0) {
      error(localize("Fusion work offsets are not supported. Set the work zero on the TC55H and use WCS offset 0."));
    }
    if (section.isMultiAxis()) {
      error(localize("Rotary and simultaneous multi-axis toolpaths are not supported by this XYZ post."));
    }
    if (section.isOptional()) {
      error(localize("Optional sections are not supported by the TC55H post."));
    }
    if (!isSameDirection(section.workPlane.forward, new Vector(0, 0, 1))) {
      error(localize("Only toolpaths aligned with the setup Z axis are supported."));
    }
    if (Vector.diff(section.workOrigin, setupOrigin).length > 0.0001 ||
        !isSameDirection(section.workPlane.forward, setupForward)) {
      error(localize("All operations must use the same Fusion setup origin and orientation."));
    }
  }
}

function validatePhysicalSpindleSpeed(physicalRpm) {
  if (typeof physicalRpm != "number" || isNaN(physicalRpm) || physicalRpm <= 0) {
    error(localize("Spindle speed must be greater than 0 RPM."));
    return;
  }
  if (physicalRpm > TC55H_MAXIMUM_PHYSICAL_SPINDLE_RPM) {
    error(localize("Spindle speed exceeds the 24000 RPM physical machine limit."));
  }
}

function getSpindleCommand(physicalRpm) {
  validatePhysicalSpindleSpeed(physicalRpm);
  var commandRpm = Math.round(physicalRpm / TC55H_SPINDLE_COMMAND_DIVISOR);
  if (commandRpm < 1) {
    error(localize("Spindle speed is too low after applying the 10:1 TC55H scaling."));
  }
  return commandRpm;
}

function validateCoordinate(value, axis) {
  if (Math.abs(value) > 99999.999) {
    error(localize(axis + " coordinate exceeds the TC55H range of +/-99999.999 mm."));
  }
}

function validateFeed(feed) {
  if (typeof feed != "number" || isNaN(feed) || feed <= 0 || feed > 99999) {
    error(localize("Feed must be greater than 0 and no more than 99999 mm/min."));
  }
}

function writeSpindleStart(physicalRpm, clockwise, includeAbsoluteMode) {
  var commandRpm = getSpindleCommand(physicalRpm);
  var directionCode = clockwise ? mFormat.format(3) : mFormat.format(4);

  if (spindleIsRunning && spindleDirectionClockwise != clockwise) {
    writeBlock(mFormat.format(5));
    spindleIsRunning = false;
  }

  if (!spindleIsRunning || spindleDirectionClockwise != clockwise) {
    writeBlock(includeAbsoluteMode ? gFormat.format(90) : "", directionCode, "S" + spindleFormat.format(commandRpm));
    spindleIsRunning = true;
    spindleDirectionClockwise = clockwise;
    lastSpindleCommand = commandRpm;
  } else if (lastSpindleCommand != commandRpm) {
    writeBlock("S" + spindleFormat.format(commandRpm));
    lastSpindleCommand = commandRpm;
  }
}

function onOpen() {
  setWordSeparator("");
  validateProgramIdentity();
  validateJob();
}

function onSection() {
  if (currentSection.getTool().getToolId() != firstToolId) {
    error(localize("Tool changes are not supported."));
    return;
  }

  setTranslation(currentSection.workOrigin);
  setRotation(currentSection.workPlane);

  var physicalRpm = tool.spindleRPM;
  var clockwise = tool.clockwise;
  writeSpindleStart(physicalRpm, clockwise, isFirstSection());

  var initialPosition = getFramePosition(currentSection.getInitialPosition());
  validateCoordinate(initialPosition.x, "X");
  validateCoordinate(initialPosition.y, "Y");
  validateCoordinate(initialPosition.z, "Z");
  if (!isFirstSection()) {
    var currentPosition = getCurrentPosition();
    if (currentPosition.z < initialPosition.z - tolerance) {
      zOutput.reset();
      writeBlock(gMotionModal.format(0), zOutput.format(initialPosition.z));
    }
  }

  xOutput.reset();
  yOutput.reset();
  writeBlock(gMotionModal.format(0), xOutput.format(initialPosition.x), yOutput.format(initialPosition.y));
  writeBlock(gMotionModal.format(0), zOutput.format(initialPosition.z));
  feedOutput.reset();
}

function onSectionEnd() {
  feedOutput.reset();
}

function onRapid(x, y, z) {
  validateCoordinate(x, "X");
  validateCoordinate(y, "Y");
  validateCoordinate(z, "Z");
  var xWord = xOutput.format(x);
  var yWord = yOutput.format(y);
  var zWord = zOutput.format(z);
  if (xWord || yWord || zWord) {
    writeBlock(gMotionModal.format(0), xWord, yWord, zWord);
    feedOutput.reset();
  }
}

function onLinear(x, y, z, feed) {
  validateCoordinate(x, "X");
  validateCoordinate(y, "Y");
  validateCoordinate(z, "Z");
  validateFeed(feed);
  var xWord = xOutput.format(x);
  var yWord = yOutput.format(y);
  var zWord = zOutput.format(z);
  if (xWord || yWord || zWord) {
    writeBlock(gMotionModal.format(1), xWord, yWord, zWord, feedOutput.format(feed));
  } else {
    feedOutput.reset();
  }
}

function onCircular(clockwise, cx, cy, cz, x, y, z, feed) {
  if (getCircularPlane() != PLANE_XY || isHelical()) {
    linearize(tolerance);
    return;
  }

  var start = getCurrentPosition();
  validateCoordinate(x, "X");
  validateCoordinate(y, "Y");
  validateCoordinate(cx - start.x, "I");
  validateCoordinate(cy - start.y, "J");
  validateFeed(feed);
  var motion = gMotionModal.format(clockwise ? 2 : 3);
  var iWord = iOutput.format(cx - start.x);
  var jWord = jOutput.format(cy - start.y);

  if (isFullCircle()) {
    writeBlock(motion, iWord, jWord, feedOutput.format(feed));
  } else {
    writeBlock(motion, xOutput.format(x), yOutput.format(y), iWord, jWord, feedOutput.format(feed));
  }
}

function onDwell(seconds) {
  if (seconds < 0.001 || seconds > 99999.999) {
    error(localize("TC55H dwell must be between 0.001 and 99999.999 seconds."));
    return;
  }
  writeBlock(gFormat.format(4), "K" + secondsFormat.format(seconds));
}

function onSpindleSpeed(physicalRpm) {
  var commandRpm = getSpindleCommand(physicalRpm);
  if (commandRpm != lastSpindleCommand) {
    writeBlock("S" + spindleFormat.format(commandRpm));
    lastSpindleCommand = commandRpm;
  }
}

function onCycle() {
  if ((typeof isProbeOperation == "function" && isProbeOperation()) ||
      String(cycleType).indexOf("probing") != -1) {
    error(localize("Probing cycles are not supported by this TC55H post."));
  }
  if (String(cycleType).indexOf("tapping") != -1) {
    error(localize("Tapping cycles require spindle synchronization and are not supported."));
  }
}

function onCyclePoint(x, y, z) {
  expandCyclePoint(x, y, z);
}

function onRadiusCompensation() {
  if (radiusCompensation != RADIUS_COMPENSATION_OFF) {
    error(localize("Control-side cutter compensation is not supported."));
  }
}

function onRapid5D() {
  error(localize("Rotary motion is not supported by this XYZ post."));
}

function onLinear5D() {
  error(localize("Rotary motion is not supported by this XYZ post."));
}

function onPassThrough() {
  error(localize("Manual passthrough commands are disabled for TC55H safety."));
}

function onComment() {
  // Generated-code comments are intentionally disabled.
}

function onCommand(command) {
  var commandId = getCommandStringId(command);
  switch (commandId) {
  case "COMMAND_COOLANT_ON":
  case "COMMAND_COOLANT_OFF":
  case "COMMAND_LOAD_TOOL":
    return;
  case "COMMAND_STOP":
    writeBlock(mFormat.format(0));
    return;
  case "COMMAND_START_SPINDLE":
  case "COMMAND_SPINDLE_CLOCKWISE":
  case "COMMAND_SPINDLE_COUNTERCLOCKWISE":
    var clockwise = commandId == "COMMAND_SPINDLE_COUNTERCLOCKWISE" ? false :
      commandId == "COMMAND_SPINDLE_CLOCKWISE" ? true : tool.clockwise;
    writeSpindleStart(spindleSpeed, clockwise, false);
    return;
  case "COMMAND_STOP_SPINDLE":
    if (spindleIsRunning) {
      writeBlock(mFormat.format(5));
      spindleIsRunning = false;
    }
    return;
  case "COMMAND_END":
    return;
  default:
    error(localize("Unsupported TC55H command requested by Fusion: " + commandId));
  }
}

function onClose() {
  writeBlock(mFormat.format(5), mFormat.format(2));
  spindleIsRunning = false;
}
