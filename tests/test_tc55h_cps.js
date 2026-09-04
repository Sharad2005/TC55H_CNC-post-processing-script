"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

function makeFormat(options) {
  function numeric(value) {
    let result = Number(value).toFixed(options.decimals || 0);
    if ((options.decimals || 0) > 0) {
      result = result.replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
    }
    if (options.zeropad) {
      const negative = result.startsWith("-");
      const unsigned = negative ? result.slice(1) : result;
      result = (negative ? "-" : "") + unsigned.padStart(options.width, "0");
    }
    return result;
  }
  return {
    format(value) { return (options.prefix || "") + numeric(value); },
    areDifferent(first, second) { return numeric(first) !== numeric(second); }
  };
}

let existingPath = "";
const context = {
  console,
  Math,
  Number,
  String,
  Array,
  isNaN,
  MM: 1,
  CAPABILITY_MILLING: 1,
  PLANE_XY: 0,
  FORMAT_REAL: 0,
  RADIUS_COMPENSATION_OFF: 0,
  setCodePage() {},
  spatial(value) { return value; },
  toRad(value) { return value * Math.PI / 180; },
  createFormat: makeFormat,
  localize(message) { return message; },
  error(message) { throw new Error(message); },
  warning() {},
  getOutputPath() { return "/output/P1.TXT"; },
  FileSystem: {
    getFilename(path) { return path.split("/").pop(); },
    getFolderPath(path) { return path.slice(0, path.lastIndexOf("/")); },
    getCombinedPath(folder, name) { return folder + "/" + name; },
    isFile(path) { return path === existingPath; }
  },
  Vector: {},
};

vm.createContext(context);
vm.runInContext(fs.readFileSync("tc55h.cps", "utf8"), context, {filename: "tc55h.cps"});

function state(x, z, safeZ = 5) {
  return {
    position: {x, y: 0, z},
    feed: 800,
    spindleRunning: true,
    spindleClockwise: true,
    spindleCommand: 1200,
    safeZ,
    plungeFeed: 200,
  };
}

function syntheticEvents(count, safeEventNumber) {
  const result = [{
    type: "spindleStart",
    clockwise: true,
    spindleCommand: 1200,
    includeAbsolute: true,
    after: state(0, 5),
  }];
  for (let number = 2; number <= count; ++number) {
    const z = number === safeEventNumber ? 5 : -2;
    result.push({
      type: number % 17 === 0 ? "arc" : "linear",
      clockwise: true,
      position: {x: number - 1, y: 0, z},
      i: 0,
      j: 1,
      feed: 800,
      fullCircle: number % 34 === 0,
      isMotion: true,
      after: state(number - 1, z),
    });
  }
  return result;
}

assert.strictEqual(context.getSpindleCommand(6000), 600);
assert.strictEqual(context.getSpindleCommand(12000), 1200);
assert.strictEqual(context.getSpindleCommand(18000), 1800);
assert.strictEqual(context.getSpindleCommand(24000), 2400);
assert.strictEqual(context.getSpindleCommand(12345), 1235);
assert.throws(() => context.getSpindleCommand(0), /greater than 0/);
assert.throws(() => context.getSpindleCommand(1), /too low/);
assert.throws(() => context.getSpindleCommand(24001), /24000 RPM/);

assert.strictEqual(context.makeLine(1, ["G90", "M03", "S2400"]), "N1 G90 M03 S2400");

const realisticOpeningEvents = [{
  type: "spindleStart",
  clockwise: true,
  spindleCommand: 1200,
  includeAbsolute: true,
  after: {
    position: {x: undefined, y: undefined, z: undefined},
    feed: undefined,
    spindleRunning: true,
    spindleClockwise: true,
    spindleCommand: 1200,
    safeZ: 5,
    plungeFeed: 200,
  },
}, {
  type: "rapid",
  position: {x: 0, y: 0, z: 5},
  isMotion: true,
  after: state(0, 5),
}];
const realisticOpeningSegments = context.partitionEvents(realisticOpeningEvents);
assert.strictEqual(realisticOpeningSegments.length, 1);
assert.strictEqual(realisticOpeningSegments[0].events.length, realisticOpeningEvents.length);

const forcedEvents = syntheticEvents(1100);
const forcedSegments = context.partitionEvents(forcedEvents);
assert.strictEqual(forcedSegments.length, 2);
assert.strictEqual(forcedSegments.reduce((sum, segment) => sum + segment.events.length, 0), forcedEvents.length);
const forcedFirst = context.renderSegment(forcedSegments[0], 0);
const forcedSecond = context.renderSegment(forcedSegments[1], 1);
assert.strictEqual(forcedFirst.length, 999);
assert.ok(forcedSecond.length <= 999);
assert.match(forcedFirst.at(-2), /^N\d+ G00 Z5$/);
assert.match(forcedFirst.at(-1), /^N\d+ M05 M02$/);
assert.strictEqual(forcedSecond[0], "N1 G90 M03 S1200");
assert.match(forcedSecond[1], /^N2 G00 X\d+ Y0$/);
assert.strictEqual(forcedSecond[2], "N3 G01 Z-2 F200");
assert.match(forcedSecond[3], /^N4 G0[123] /);
assert.match(forcedSecond[3], / F800$/);

for (const line of [...forcedFirst, ...forcedSecond]) {
  assert.ok(!line.startsWith(" ") && !line.endsWith(" "));
  assert.ok(!line.includes("  "));
  assert.match(line, /^N\d+(?: [A-Z][+-]?(?:\d+(?:\.\d*)?|\.\d+))+$/);
}

const naturalEvents = syntheticEvents(1100, 950);
const naturalSegments = context.partitionEvents(naturalEvents);
assert.strictEqual(naturalSegments[0].events.length, 950);
const naturalFirst = context.renderSegment(naturalSegments[0], 0);
assert.doesNotMatch(naturalFirst.at(-2), /G00 Z5$/);
assert.match(naturalFirst.at(-1), /M05 M02$/);

const oldMaximumBlocks = context.TC55H_MAXIMUM_PROGRAM_BLOCKS;
const oldMaximumFiles = context.TC55H_MAXIMUM_SEQUENCE_FILES;
context.TC55H_MAXIMUM_PROGRAM_BLOCKS = 10;
context.TC55H_MAXIMUM_SEQUENCE_FILES = 3;
assert.throws(() => context.partitionEvents(syntheticEvents(40)), /99-file/);
context.TC55H_MAXIMUM_PROGRAM_BLOCKS = oldMaximumBlocks;
context.TC55H_MAXIMUM_SEQUENCE_FILES = oldMaximumFiles;

context.baseProgramNumber = 9999;
assert.throws(() => context.preflightSequenceFiles([{}, {}]), /P9999/);
context.baseProgramNumber = 1;
existingPath = "/output/P2.TXT";
assert.throws(() => context.preflightSequenceFiles([{}, {}]), /already exists/);

console.log("OK: tc55h.cps scaling, spacing, splitting, handoff, and limits");
