/**
  TC55H post processor for Autodesk Fusion.

  Derived from the Autodesk Grbl post supplied with this project.
  Copyright (C) 2012-2026 by Autodesk, Inc.
  TC55H adaptation Copyright (C) 2026.

  Target controller:
    2016K_TC55H(B)_V2.0 / 2016KTC55H(T)_V1.0
    Software TC55HV4005Z00000

  Release: 1.0.0 (dual-CAM community handoff)
  Controller-output contract: TC55H Baseline 1.0
*/

description = "TopCNC TC55H (CM45L, XYZ, continuation files)";
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

// The controller documents 999 lines, but the target V4.005 unit became
// unresponsive near that limit. Keep operational files at or below 900.
var TC55H_OPERATIONAL_BLOCK_LIMIT = 900;
var TC55H_MAXIMUM_SEQUENCE_FILES = 99;
var TC55H_SAFE_SPLIT_LOOKBACK = 100;
var TC55H_MAXIMUM_PHYSICAL_SPINDLE_RPM = 24000;
var TC55H_SPINDLE_COMMAND_DIVISOR = 10;

// Future coolant support belongs here. Map verified TC55H M51-M66 GPIO
// commands only after the controller I/O assignment and electrical behavior
// are known. Coolant requests are intentionally silent everywhere else.

var xyzFormat = createFormat({decimals:3, type:FORMAT_REAL});
var feedFormat = createFormat({decimals:0});
var spindleFormat = createFormat({decimals:0});
var secondsFormat = createFormat({decimals:3, type:FORMAT_REAL});
var gFormat = createFormat({prefix:"G", decimals:0, width:2, zeropad:true});
var mFormat = createFormat({prefix:"M", decimals:0, width:2, zeropad:true});

var events = [];
var baseProgramNumber;
var firstToolId;
var setupOrigin;
var setupForward;

var jobState = {
  position        : {x:undefined, y:undefined, z:undefined},
  feed            : undefined,
  spindleRunning  : false,
  spindleClockwise: true,
  spindleCommand  : undefined,
  safeZ           : undefined,
  plungeFeed      : undefined
};

function copyPosition(position) {
  return {x:position.x, y:position.y, z:position.z};
}

function copyState(state) {
  return {
    position        : copyPosition(state.position),
    feed            : state.feed,
    spindleRunning  : state.spindleRunning,
    spindleClockwise: state.spindleClockwise,
    spindleCommand  : state.spindleCommand,
    safeZ           : state.safeZ,
    plungeFeed      : state.plungeFeed
  };
}

function coordinateIsDifferent(first, second) {
  if (first == undefined && second == undefined) {
    return false;
  }
  return first == undefined || second == undefined || xyzFormat.areDifferent(first, second);
}

function feedIsDifferent(first, second) {
  if (first == undefined && second == undefined) {
    return false;
  }
  return first == undefined || second == undefined || feedFormat.areDifferent(first, second);
}

function appendEvent(event) {
  event.after = copyState(jobState);
  events.push(event);
}

function validateProgramIdentity() {
  var match = programName && /^P([0-9]{1,4})$/.exec(String(programName));
  if (!match) {
    error(localize("Program name must be uppercase P followed by 1 to 4 digits, for example P1."));
    return;
  }
  baseProgramNumber = Number(match[1]);
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
      error(localize("Fusion work offsets are not supported. Set work zero on the TC55H and use WCS offset 0."));
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
  if (value != undefined && Math.abs(value) > 99999.999) {
    error(localize(axis + " coordinate exceeds the TC55H range of +/-99999.999 mm."));
  }
}

function validateFeed(feed) {
  if (typeof feed != "number" || isNaN(feed) || feed <= 0 || feed > 99999) {
    error(localize("Feed must be greater than 0 and no more than 99999 mm/min."));
  }
}

function queueSpindleStart(physicalRpm, clockwise, includeAbsoluteMode) {
  var commandRpm = getSpindleCommand(physicalRpm);
  if (jobState.spindleRunning && jobState.spindleClockwise != clockwise) {
    queueSpindleStop();
  }
  if (!jobState.spindleRunning || jobState.spindleClockwise != clockwise) {
    jobState.spindleRunning = true;
    jobState.spindleClockwise = clockwise;
    jobState.spindleCommand = commandRpm;
    appendEvent({type:"spindleStart", clockwise:clockwise, spindleCommand:commandRpm, includeAbsolute:includeAbsoluteMode});
  } else if (jobState.spindleCommand != commandRpm) {
    queueSpindleSpeed(physicalRpm);
  }
}

function queueSpindleSpeed(physicalRpm) {
  var commandRpm = getSpindleCommand(physicalRpm);
  if (jobState.spindleCommand != commandRpm) {
    jobState.spindleCommand = commandRpm;
    appendEvent({type:"spindleSpeed", spindleCommand:commandRpm});
  }
}

function queueSpindleStop() {
  if (jobState.spindleRunning) {
    jobState.spindleRunning = false;
    appendEvent({type:"spindleStop"});
  }
}

function queueRapid(x, y, z) {
  validateCoordinate(x, "X");
  validateCoordinate(y, "Y");
  validateCoordinate(z, "Z");
  var changed = coordinateIsDifferent(x, jobState.position.x) ||
    coordinateIsDifferent(y, jobState.position.y) ||
    coordinateIsDifferent(z, jobState.position.z);
  if (!changed) {
    return;
  }
  if (x != undefined) {jobState.position.x = x;}
  if (y != undefined) {jobState.position.y = y;}
  if (z != undefined) {jobState.position.z = z;}
  appendEvent({type:"rapid", position:copyPosition(jobState.position), isMotion:true});
}

function queueSectionInitialPosition(initialPosition, firstSection) {
  if (firstSection) {
    // On the first section the controller's current XY position is unknown.
    // Reach Fusion's clearance Z before making any horizontal rapid move.
    queueRapid(undefined, undefined, initialPosition.z);
    queueRapid(initialPosition.x, initialPosition.y, initialPosition.z);
    return;
  }
  if (jobState.position.z < initialPosition.z - tolerance) {
    queueRapid(jobState.position.x, jobState.position.y, initialPosition.z);
  }
  queueRapid(initialPosition.x, initialPosition.y, jobState.position.z);
  queueRapid(initialPosition.x, initialPosition.y, initialPosition.z);
}

function queueLinear(x, y, z, feed) {
  validateCoordinate(x, "X");
  validateCoordinate(y, "Y");
  validateCoordinate(z, "Z");
  validateFeed(feed);
  var changed = coordinateIsDifferent(x, jobState.position.x) ||
    coordinateIsDifferent(y, jobState.position.y) ||
    coordinateIsDifferent(z, jobState.position.z);
  if (!changed) {
    return;
  }
  jobState.position = {x:x, y:y, z:z};
  jobState.feed = feed;
  appendEvent({type:"linear", position:copyPosition(jobState.position), feed:feed, isMotion:true});
}

function queueArc(clockwise, cx, cy, x, y, z, feed, fullCircle) {
  validateCoordinate(x, "X");
  validateCoordinate(y, "Y");
  validateCoordinate(z, "Z");
  validateFeed(feed);
  var start = copyPosition(jobState.position);
  var i = cx - start.x;
  var j = cy - start.y;
  validateCoordinate(i, "I");
  validateCoordinate(j, "J");
  jobState.position = {x:x, y:y, z:z};
  jobState.feed = feed;
  appendEvent({type:"arc", clockwise:clockwise, position:copyPosition(jobState.position), i:i, j:j, feed:feed, fullCircle:fullCircle, isMotion:true});
}

function onOpen() {
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
  var initialPosition = getFramePosition(currentSection.getInitialPosition());
  validateCoordinate(initialPosition.x, "X");
  validateCoordinate(initialPosition.y, "Y");
  validateCoordinate(initialPosition.z, "Z");
  jobState.safeZ = initialPosition.z;
  jobState.plungeFeed = hasParameter("operation:tool_feedPlunge") ? getParameter("operation:tool_feedPlunge") : undefined;
  if (jobState.plungeFeed != undefined) {
    validateFeed(jobState.plungeFeed);
  }
  queueSpindleStart(tool.spindleRPM, tool.clockwise, isFirstSection());
  queueSectionInitialPosition(initialPosition, isFirstSection());
}

function onRapid(x, y, z) {
  queueRapid(x, y, z);
}

function onLinear(x, y, z, feed) {
  queueLinear(x, y, z, feed);
}

function onCircular(clockwise, cx, cy, cz, x, y, z, feed) {
  if (getCircularPlane() != PLANE_XY || isHelical()) {
    linearize(tolerance);
    return;
  }
  queueArc(clockwise, cx, cy, x, y, z, feed, isFullCircle());
}

function onDwell(seconds) {
  if (seconds < 0.001 || seconds > 99999.999) {
    error(localize("TC55H dwell must be between 0.001 and 99999.999 seconds."));
    return;
  }
  appendEvent({type:"dwell", seconds:seconds});
}

function onSpindleSpeed(physicalRpm) {
  queueSpindleSpeed(physicalRpm);
}

function onCycle() {
  if ((typeof isProbeOperation == "function" && isProbeOperation()) || String(cycleType).indexOf("probing") != -1) {
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
    appendEvent({type:"pause"});
    return;
  case "COMMAND_START_SPINDLE":
  case "COMMAND_SPINDLE_CLOCKWISE":
  case "COMMAND_SPINDLE_COUNTERCLOCKWISE":
    var clockwise = commandId == "COMMAND_SPINDLE_COUNTERCLOCKWISE" ? false :
      commandId == "COMMAND_SPINDLE_CLOCKWISE" ? true : tool.clockwise;
    queueSpindleStart(spindleSpeed, clockwise, false);
    return;
  case "COMMAND_STOP_SPINDLE":
    queueSpindleStop();
    return;
  case "COMMAND_END":
    return;
  default:
    error(localize("Unsupported TC55H command requested by Fusion: " + commandId));
  }
}

function getHandoffZ(state) {
  if (state.position.z == undefined || state.safeZ == undefined) {
    error(localize("Cannot split before a known position and Fusion clearance Z are available."));
  }
  return Math.max(state.position.z, state.safeZ);
}

function canHandoffAtState(state) {
  if (!state || !state.position ||
      state.position.x == undefined || state.position.y == undefined || state.position.z == undefined ||
      state.safeZ == undefined) {
    return false;
  }
  var requiresDescent = xyzFormat.areDifferent(Math.max(state.position.z, state.safeZ), state.position.z);
  return !requiresDescent || state.plungeFeed != undefined || state.feed != undefined;
}

function needsHandoffRetract(state) {
  return coordinateIsDifferent(getHandoffZ(state), state.position.z);
}

function getContinuationOpeningCount(state) {
  var count = 1;
  if (state.position.x != undefined || state.position.y != undefined) {
    ++count;
  }
  if (needsHandoffRetract(state)) {
    ++count;
  }
  return count;
}

function getIntermediateEndingCount(state) {
  if (state.position.z == undefined || state.safeZ == undefined) {
    return 2;
  }
  return (needsHandoffRetract(state) ? 1 : 0) + 1;
}

function isNaturalSafeBoundary(event) {
  var state = event.after;
  return event.isMotion && state.position.z != undefined && state.safeZ != undefined &&
    !xyzFormat.areDifferent(Math.max(state.position.z, state.safeZ), state.position.z);
}

function partitionEvents(sourceEvents) {
  var segments = [];
  var start = 0;
  var startState;
  while (start < sourceEvents.length) {
    var openingCount = segments.length == 0 ? 0 : getContinuationOpeningCount(startState);
    var maximumEnd = start;
    for (var end = start + 1; end <= sourceEvents.length; ++end) {
      var boundaryState = sourceEvents[end - 1].after;
      var endingCount = end == sourceEvents.length ? 1 : getIntermediateEndingCount(boundaryState);
      if (openingCount + (end - start) + endingCount > TC55H_OPERATIONAL_BLOCK_LIMIT) {
        break;
      }
      if (end == sourceEvents.length || canHandoffAtState(boundaryState)) {
        maximumEnd = end;
      }
    }
    if (maximumEnd == start) {
      error(localize("Continuation overhead leaves no room for a machining block."));
      return [];
    }
    var chosenEnd = maximumEnd;
    if (maximumEnd < sourceEvents.length) {
      var earliestSafeCandidate = Math.max(start + 1, maximumEnd - TC55H_SAFE_SPLIT_LOOKBACK);
      for (var candidate = maximumEnd; candidate >= earliestSafeCandidate; --candidate) {
        if (isNaturalSafeBoundary(sourceEvents[candidate - 1])) {
          chosenEnd = candidate;
          break;
        }
      }
    }
    var endState = sourceEvents[chosenEnd - 1].after;
    segments.push({events:sourceEvents.slice(start, chosenEnd), startState:segments.length == 0 ? undefined : copyState(startState), endState:copyState(endState), isFinal:chosenEnd == sourceEvents.length});
    start = chosenEnd;
    startState = copyState(endState);
    if (segments.length > TC55H_MAXIMUM_SEQUENCE_FILES) {
      error(localize("TC55H sequence exceeds the 99-file controller limit."));
      return [];
    }
  }
  return segments;
}

function formatAxis(letter, value) {
  return value == undefined ? "" : letter + xyzFormat.format(value);
}

function formatFeed(feed) {
  return "F" + feedFormat.format(feed);
}

function formatSpindle(command) {
  return "S" + spindleFormat.format(command);
}

function makeLine(sequence, words) {
  var filtered = [];
  for (var wordIndex = 0; wordIndex < words.length; ++wordIndex) {
    if (words[wordIndex]) {
      filtered.push(words[wordIndex]);
    }
  }
  if (filtered.length == 0) {
    error(localize("Attempted to create an empty TC55H program block."));
  }
  return "N" + sequence + " " + filtered.join(" ");
}

function appendRenderedLine(lines, words) {
  if (lines.length >= TC55H_OPERATIONAL_BLOCK_LIMIT) {
    error(localize("Rendered TC55H continuation exceeds the 900-block operational limit."));
    return;
  }
  lines.push(makeLine(lines.length + 1, words));
}

function createRenderState() {
  return {position:{x:undefined, y:undefined, z:undefined}, motion:undefined, feed:undefined, forceMotion:false, forceFeed:false};
}

function renderMotion(event, state) {
  var words = [];
  var motionCode = event.type == "rapid" ? 0 : event.type == "linear" ? 1 : event.clockwise ? 2 : 3;
  if (state.forceMotion || state.motion != motionCode) {
    words.push(gFormat.format(motionCode));
  }
  if (event.type == "arc") {
    if (!event.fullCircle) {
      if (coordinateIsDifferent(event.position.x, state.position.x)) {words.push(formatAxis("X", event.position.x));}
      if (coordinateIsDifferent(event.position.y, state.position.y)) {words.push(formatAxis("Y", event.position.y));}
    }
    words.push(formatAxis("I", event.i));
    words.push(formatAxis("J", event.j));
    if (state.forceFeed || feedIsDifferent(event.feed, state.feed)) {words.push(formatFeed(event.feed));}
  } else {
    if (coordinateIsDifferent(event.position.x, state.position.x)) {words.push(formatAxis("X", event.position.x));}
    if (coordinateIsDifferent(event.position.y, state.position.y)) {words.push(formatAxis("Y", event.position.y));}
    if (coordinateIsDifferent(event.position.z, state.position.z)) {words.push(formatAxis("Z", event.position.z));}
    if (event.type == "linear" && (state.forceFeed || feedIsDifferent(event.feed, state.feed))) {words.push(formatFeed(event.feed));}
  }
  state.position = copyPosition(event.position);
  state.motion = motionCode;
  if (event.feed != undefined) {state.feed = event.feed;}
  state.forceMotion = false;
  state.forceFeed = false;
  return words;
}

function renderEvent(event, state) {
  switch (event.type) {
  case "rapid":
  case "linear":
  case "arc":
    return renderMotion(event, state);
  case "spindleStart":
    return [event.includeAbsolute ? gFormat.format(90) : "", event.clockwise ? mFormat.format(3) : mFormat.format(4), formatSpindle(event.spindleCommand)];
  case "spindleSpeed":
    return [formatSpindle(event.spindleCommand)];
  case "spindleStop":
    return [mFormat.format(5)];
  case "pause":
    return [mFormat.format(0)];
  case "dwell":
    return [gFormat.format(4), "K" + secondsFormat.format(event.seconds)];
  default:
    error(localize("Unknown buffered TC55H event: " + event.type));
    return [];
  }
}

function getResumeFeed(state) {
  var resumeFeed = state.plungeFeed != undefined ? state.plungeFeed : state.feed;
  validateFeed(resumeFeed);
  return resumeFeed;
}

function renderContinuationOpening(lines, state, renderState) {
  var startWords = [gFormat.format(90)];
  if (state.spindleRunning) {
    startWords.push(state.spindleClockwise ? mFormat.format(3) : mFormat.format(4));
    startWords.push(formatSpindle(state.spindleCommand));
  }
  appendRenderedLine(lines, startWords);
  var handoffZ = getHandoffZ(state);
  if (state.position.x != undefined || state.position.y != undefined) {
    appendRenderedLine(lines, [gFormat.format(0), formatAxis("X", state.position.x), formatAxis("Y", state.position.y)]);
  }
  if (coordinateIsDifferent(handoffZ, state.position.z)) {
    var resumeFeed = getResumeFeed(state);
    appendRenderedLine(lines, [gFormat.format(1), formatAxis("Z", state.position.z), formatFeed(resumeFeed)]);
    renderState.motion = 1;
    renderState.feed = resumeFeed;
  } else {
    renderState.motion = 0;
  }
  renderState.position = copyPosition(state.position);
  renderState.forceMotion = true;
  renderState.forceFeed = true;
}

function renderIntermediateEnding(lines, state) {
  var handoffZ = getHandoffZ(state);
  if (coordinateIsDifferent(handoffZ, state.position.z)) {
    appendRenderedLine(lines, [gFormat.format(0), formatAxis("Z", handoffZ)]);
  }
  appendRenderedLine(lines, [mFormat.format(5), mFormat.format(2)]);
}

function renderSegment(segment, segmentIndex) {
  var lines = [];
  var renderState = createRenderState();
  if (segmentIndex > 0) {
    renderContinuationOpening(lines, segment.startState, renderState);
  }
  for (var eventIndex = 0; eventIndex < segment.events.length; ++eventIndex) {
    appendRenderedLine(lines, renderEvent(segment.events[eventIndex], renderState));
  }
  if (segment.isFinal) {
    appendRenderedLine(lines, [mFormat.format(5), mFormat.format(2)]);
  } else {
    renderIntermediateEnding(lines, segment.endState);
  }
  return lines;
}

function getSequencePath(sequenceNumber) {
  return FileSystem.getCombinedPath(FileSystem.getFolderPath(getOutputPath()), "P" + sequenceNumber + ".TXT");
}

function preflightSequenceFiles(segments) {
  if (baseProgramNumber + segments.length - 1 > 9999) {
    error(localize("Continuation filenames would exceed P9999.TXT."));
  }
  for (var segmentIndex = 1; segmentIndex < segments.length; ++segmentIndex) {
    var path = getSequencePath(baseProgramNumber + segmentIndex);
    if (FileSystem.isFile(path)) {
      error(localize("Continuation file already exists; move or delete it before posting: " + FileSystem.getFilename(path)));
    }
  }
}

function writeLines(lines) {
  for (var lineIndex = 0; lineIndex < lines.length; ++lineIndex) {
    writeln(lines[lineIndex]);
  }
}

function writeSequence() {
  var segments = partitionEvents(events);
  preflightSequenceFiles(segments);
  var renderedSegments = [];
  for (var segmentIndex = 0; segmentIndex < segments.length; ++segmentIndex) {
    renderedSegments.push(renderSegment(segments[segmentIndex], segmentIndex));
  }
  writeLines(renderedSegments[0]);
  var generatedNames = ["P" + baseProgramNumber + ".TXT"];
  for (var continuationIndex = 1; continuationIndex < renderedSegments.length; ++continuationIndex) {
    var continuationNumber = baseProgramNumber + continuationIndex;
    var continuationPath = getSequencePath(continuationNumber);
    redirectToFile(continuationPath);
    writeLines(renderedSegments[continuationIndex]);
    closeRedirection();
    generatedNames.push("P" + continuationNumber + ".TXT");
  }
  warning(localize("Generated TC55H sequence: " + generatedNames.join(", ")));
}

function onClose() {
  writeSequence();
}
