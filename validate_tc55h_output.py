#!/usr/bin/env python3
"""Validate one TC55H program or an ordered continuation sequence."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


PROGRAM_NAME = re.compile(r"^P([0-9]{1,4})\.TXT$")
SEQUENCE_WORD = re.compile(r"^N([1-9][0-9]*)$")
WORD = re.compile(r"^([A-Z])([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))$")
ALLOWED_G = {0, 1, 2, 3, 4, 90}
ALLOWED_M = {0, 2, 3, 4, 5}
ALLOWED_LETTERS = {"G", "M", "X", "Y", "Z", "I", "J", "K", "F", "S"}
MAX_BLOCKS = 900
MAX_FILES = 99


@dataclass
class MachineState:
    x: float | None = None
    y: float | None = None
    z: float | None = None
    feed: float | None = None
    motion: int | None = None
    spindle_running: bool = False
    spindle_clockwise: bool = True
    spindle_command: int | None = None

    def copy(self) -> "MachineState":
        return MachineState(**vars(self))


@dataclass
class Block:
    sequence: int
    words: list[tuple[str, str]]
    before: MachineState
    after: MachineState

    def values(self, letter: str) -> list[float]:
        return [float(value) for address, value in self.words if address == letter]

    def has_g(self, code: int) -> bool:
        return code in [int(value) for value in self.values("G")]

    def has_m(self, code: int) -> bool:
        return code in [int(value) for value in self.values("M")]


@dataclass
class Program:
    path: Path
    number: int
    blocks: list[Block] = field(default_factory=list)


def fail(path: Path, line_number: int | None, message: str) -> None:
    location = str(path) if line_number is None else f"{path}:{line_number}"
    raise ValueError(f"{location}: {message}")


def parse_line(path: Path, line_number: int, line: str) -> tuple[int, list[tuple[str, str]]]:
    if line != line.strip(" "):
        fail(path, line_number, "leading or trailing spaces are not permitted")
    if "  " in line:
        fail(path, line_number, "words must be separated by exactly one space")
    if any(character.isspace() and character != " " for character in line):
        fail(path, line_number, "only ASCII spaces may separate words")

    fields = line.split(" ")
    sequence_match = SEQUENCE_WORD.fullmatch(fields[0]) if fields else None
    if not sequence_match:
        fail(path, line_number, "block must start with a standalone N sequence word")
    if len(fields) < 2:
        fail(path, line_number, "block contains no executable words")

    words: list[tuple[str, str]] = []
    for field_text in fields[1:]:
        match = WORD.fullmatch(field_text)
        if not match:
            fail(path, line_number, f"invalid or unsupported word {field_text!r}")
        words.append((match.group(1), match.group(2)))
    return int(sequence_match.group(1)), words


def validate_words(path: Path, line_number: int, words: list[tuple[str, str]], state: MachineState) -> None:
    letters = [letter for letter, _ in words]
    if any(letter not in ALLOWED_LETTERS for letter in letters):
        fail(path, line_number, "block contains an unsupported address")

    g_codes = [int(float(value)) for letter, value in words if letter == "G"]
    m_codes = [int(float(value)) for letter, value in words if letter == "M"]
    if any(code not in ALLOWED_G for code in g_codes):
        fail(path, line_number, f"unsupported G code in {g_codes}")
    if any(code not in ALLOWED_M for code in m_codes):
        fail(path, line_number, f"unsupported M code in {m_codes}")

    for letter, value_text in words:
        value = float(value_text)
        if letter in {"G", "M"} and not re.fullmatch(r"[0-9]{2}", value_text):
            fail(path, line_number, f"{letter} must use exactly two unsigned digits")
        if letter in {"F", "S"} and not re.fullmatch(r"[1-9][0-9]*", value_text):
            fail(path, line_number, f"{letter} must be an unpadded positive whole number")
        if letter in {"X", "Y", "Z", "I", "J", "K"} and "." in value_text:
            if len(value_text.split(".", 1)[1]) > 3:
                fail(path, line_number, f"{letter} may have at most three fractional digits")
        if letter in {"G", "M", "F", "S"} and not value.is_integer():
            fail(path, line_number, f"{letter} must be a whole number")
        if letter in {"X", "Y", "Z", "I", "J"} and abs(value) > 99999.999:
            fail(path, line_number, f"{letter} exceeds the controller range")
        if letter == "F" and not 0 < value <= 99999:
            fail(path, line_number, "F must be greater than 0 and no more than 99999")
        if letter == "S" and not 1 <= value <= 2400:
            fail(path, line_number, "S must be between 1 and 2400")
        if letter == "K" and not 0.001 <= value <= 99999.999:
            fail(path, line_number, "K must be between 0.001 and 99999.999")

    motion_codes = [code for code in g_codes if code in {0, 1, 2, 3}]
    if len(motion_codes) > 1:
        fail(path, line_number, "only one motion G code is permitted in a block")
    effective_motion = motion_codes[-1] if motion_codes else state.motion
    is_dwell = 4 in g_codes
    is_arc = effective_motion in {2, 3}
    if ("K" in letters) != is_dwell:
        fail(path, line_number, "K is required only and always with G04")
    if ("I" in letters or "J" in letters) and not is_arc:
        fail(path, line_number, "I/J is only valid during G02/G03")
    if is_arc and any(letter in letters for letter in {"X", "Y", "I", "J"}) and not {"I", "J"}.issubset(letters):
        fail(path, line_number, "an arc block requires both I and J")


def apply_words(words: list[tuple[str, str]], state: MachineState) -> None:
    for letter, value_text in words:
        value = float(value_text)
        if letter == "G" and int(value) in {0, 1, 2, 3}:
            state.motion = int(value)
        elif letter == "X":
            state.x = value
        elif letter == "Y":
            state.y = value
        elif letter == "Z":
            state.z = value
        elif letter == "F":
            state.feed = value
        elif letter == "S":
            state.spindle_command = int(value)
        elif letter == "M" and int(value) in {3, 4}:
            state.spindle_running = True
            state.spindle_clockwise = int(value) == 3
        elif letter == "M" and int(value) == 5:
            state.spindle_running = False


def validate(path: Path) -> Program:
    name_match = PROGRAM_NAME.fullmatch(path.name)
    if not name_match:
        fail(path, None, "filename must be P followed by 1-4 digits and .TXT")
    try:
        text = path.read_bytes().decode("ascii")
    except UnicodeDecodeError as exc:
        fail(path, exc.start, "file is not ASCII")

    lines = text.splitlines()
    if not lines:
        fail(path, None, "program is empty")
    if len(lines) > MAX_BLOCKS:
        fail(path, None, f"program has {len(lines)} blocks; maximum is {MAX_BLOCKS}")
    if any(not line for line in lines):
        fail(path, None, "blank lines are not permitted")

    program = Program(path=path, number=int(name_match.group(1)))
    state = MachineState()
    for expected_sequence, line in enumerate(lines, start=1):
        sequence, words = parse_line(path, expected_sequence, line)
        if sequence != expected_sequence:
            fail(path, expected_sequence, f"expected N{expected_sequence}")
        before = state.copy()
        validate_words(path, expected_sequence, words, state)
        apply_words(words, state)
        program.blocks.append(Block(sequence, words, before, state.copy()))

    final = program.blocks[-1]
    if final.words != [("M", "05"), ("M", "02")]:
        fail(path, len(lines), "final block must be exactly M05 M02")
    return program


def close_enough(first: float | None, second: float | None) -> bool:
    return first is not None and second is not None and abs(first - second) <= 0.0005


def validate_handoff(previous: Program, following: Program) -> None:
    start = following.blocks[0]
    if not start.has_g(90):
        fail(following.path, 1, "continuation must begin with G90")

    previous_end_state = previous.blocks[-1].before
    if previous_end_state.spindle_running and previous_end_state.spindle_command is not None:
        expected_m = 3 if previous_end_state.spindle_clockwise else 4
        if not start.has_m(expected_m) or start.values("S") != [float(previous_end_state.spindle_command)]:
            fail(following.path, 1, "continuation does not restore spindle direction and speed")
    elif start.has_m(3) or start.has_m(4):
        fail(following.path, 1, "continuation restarts a spindle that was previously stopped")

    if len(following.blocks) < 2 or not following.blocks[1].has_g(0):
        fail(following.path, 2, "continuation must rapid to the saved X/Y")
    xy_block = following.blocks[1]
    x_values = xy_block.values("X")
    y_values = xy_block.values("Y")
    if not x_values or not y_values:
        fail(following.path, 2, "continuation X/Y positioning must be explicit")
    if not close_enough(x_values[-1], previous_end_state.x) or not close_enough(y_values[-1], previous_end_state.y):
        fail(following.path, 2, "continuation X/Y does not match the preceding endpoint")

    if len(previous.blocks) >= 2:
        possible_retract = previous.blocks[-2]
        z_values = possible_retract.values("Z")
        is_handoff_retract = possible_retract.has_g(0) and bool(z_values) and not possible_retract.values("X") and not possible_retract.values("Y")
        descent = following.blocks[2] if len(following.blocks) >= 3 else None
        has_descent = descent is not None and descent.has_g(1) and bool(descent.values("Z")) and bool(descent.values("F")) and not descent.values("X") and not descent.values("Y")
        if has_descent:
            if not is_handoff_retract:
                fail(following.path, 3, "continuation descends even though no preceding Z handoff was found")
            if not close_enough(descent.values("Z")[-1], possible_retract.before.z):
                fail(following.path, 3, "continuation Z does not restore the saved cutting endpoint")


def validate_sequence(paths: list[Path]) -> list[Program]:
    if not paths:
        raise ValueError("no TC55H files supplied")
    if len(paths) > MAX_FILES:
        raise ValueError(f"sequence has {len(paths)} files; maximum is {MAX_FILES}")
    programs = [validate(path) for path in paths]
    for index, program in enumerate(programs):
        expected_number = programs[0].number + index
        if program.number != expected_number:
            fail(program.path, None, f"expected continuation filename P{expected_number}.TXT")
    for previous, following in zip(programs, programs[1:]):
        validate_handoff(previous, following)
    return programs


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {Path(sys.argv[0]).name} P1.TXT [P2.TXT ...]", file=sys.stderr)
        return 2
    try:
        programs = validate_sequence([Path(argument) for argument in sys.argv[1:]])
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    total = sum(len(program.blocks) for program in programs)
    print(f"OK: {len(programs)} file(s), {total} total blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
