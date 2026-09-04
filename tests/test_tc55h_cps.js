"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const output = [];

function makeFormat(options) {
  return {
    format(value) {
      let result = Number(value).toFixed(options.decimals || 0);
      if ((options.decimals || 0) > 0) {
        result = result.replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
      }
      if (options.zeropad) {
        const negative = result.startsWith("-");
        const unsigned = negative ? result.slice(1) : result;
        result = (negative ? "-" : "") + unsigned.padStart(options.width, "0");
      }
      return (options.prefix || "") + result;
    }
  };
}

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
  CONTROL_FORCE: 0,
  setCodePage() {},
  spatial(value) { return value; },
  toRad(value) { return value * Math.PI / 180; },
  createFormat: makeFormat,
  createOutputVariable() { return {format() { return ""; }, reset() {}}; },
  formatWords(args) { return Array.from(args).filter(Boolean).join(""); },
  writeWords(...words) { output.push(words.join("")); },
  localize(message) { return message; },
  error(message) { throw new Error(message); },
  Vector: {},
};

vm.createContext(context);
vm.runInContext(fs.readFileSync("tc55h.cps", "utf8"), context, {filename: "tc55h.cps"});

assert.strictEqual(context.getSpindleCommand(6000), 600);
assert.strictEqual(context.getSpindleCommand(12000), 1200);
assert.strictEqual(context.getSpindleCommand(18000), 1800);
assert.strictEqual(context.getSpindleCommand(24000), 2400);
assert.strictEqual(context.getSpindleCommand(12345), 1235);
assert.throws(() => context.getSpindleCommand(0), /greater than 0/);
assert.throws(() => context.getSpindleCommand(1), /too low/);
assert.throws(() => context.getSpindleCommand(24001), /24000 RPM/);

context.writeBlock("G90", "M03", "S2400");
assert.deepStrictEqual(output, ["N1G90M03S2400"]);

context.emittedBlockCount = 999;
assert.throws(() => context.writeBlock("G00", "X0"), /999-block/);

console.log("OK: tc55h.cps spindle scaling and block gate");
