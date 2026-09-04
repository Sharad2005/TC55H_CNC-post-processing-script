#!/usr/bin/env python3
"""Validate a generated TC55H TXT program against the project output contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path


PROGRAM_NAME = re.compile(r"^P[0-9]{1,4}\.TXT$", re.IGNORECASE)
WORD = re.compile(r"([A-Z])([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))")
ALLOWED_G = {0, 1, 2, 3, 4, 90}
ALLOWED_M = {0, 2, 3, 4, 5}
ALLOWED_LETTERS = {"G", "M", "X", "Y", "Z", "I", "J", "K", "F", "S"}
MAX_BLOCKS = 999


def fail(path: Path, line_number: int | None, message: str) -> None:
    location = str(path) if line_number is None else f"{path}:{line_number}"
    raise ValueError(f"{location}: {message}")


def parse_words(path: Path, line_number: int, body: str) -> list[tuple[str, str]]:
    words: list[tuple[str, str]] = []
    position = 0
    while position < len(body):
        match = WORD.match(body, position)
        if not match:
            fail(path, line_number, f"invalid or unsupported text at {body[position:]!r}")
        words.append((match.group(1), match.group(2)))
        position = match.end()
    if not words:
        fail(path, line_number, "block contains no executable words")
    return words


def validate(path: Path) -> None:
    if not PROGRAM_NAME.fullmatch(path.name):
        fail(path, None, "filename must be P followed by 1-4 digits and .TXT")

    try:
        raw = path.read_bytes()
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        fail(path, exc.start, "file is not ASCII")

    lines = text.splitlines()
    if not lines:
        fail(path, None, "program is empty")
    if len(lines) > MAX_BLOCKS:
        fail(path, None, f"program has {len(lines)} blocks; maximum is {MAX_BLOCKS}")
    if any(not line for line in lines):
        fail(path, None, "blank lines are not permitted")

    for expected_sequence, line in enumerate(lines, start=1):
        if any(character.isspace() for character in line):
            fail(path, expected_sequence, "whitespace is not permitted")

        sequence = re.match(r"^N([0-9]+)", line)
        if not sequence:
            fail(path, expected_sequence, "block must start with an N sequence number")
        if int(sequence.group(1)) != expected_sequence:
            fail(path, expected_sequence, f"expected N{expected_sequence}")

        words = parse_words(path, expected_sequence, line[sequence.end():])
        letters = [letter for letter, _ in words]
        if any(letter not in ALLOWED_LETTERS for letter in letters):
            fail(path, expected_sequence, "block contains an unsupported address")

        g_codes = [int(float(value)) for letter, value in words if letter == "G"]
        m_codes = [int(float(value)) for letter, value in words if letter == "M"]
        if any(code not in ALLOWED_G for code in g_codes):
            fail(path, expected_sequence, f"unsupported G code in {g_codes}")
        if any(code not in ALLOWED_M for code in m_codes):
            fail(path, expected_sequence, f"unsupported M code in {m_codes}")

        for letter, value_text in words:
            value = float(value_text)
            if letter in {"G", "M", "F", "S"} and not value.is_integer():
                fail(path, expected_sequence, f"{letter} must be a whole number")
            if letter in {"X", "Y", "Z", "I", "J"} and abs(value) > 99999.999:
                fail(path, expected_sequence, f"{letter} exceeds the controller range")
            if letter == "F" and not 0 <= value <= 99999:
                fail(path, expected_sequence, "F must be between 0 and 99999")
            if letter == "S" and not 1 <= value <= 2400:
                fail(path, expected_sequence, "S must be between 1 and 2400")
            if letter == "K" and not 0.001 <= value <= 99999.999:
                fail(path, expected_sequence, "K must be between 0.001 and 99999.999")

        is_dwell = 4 in g_codes
        is_arc = 2 in g_codes or 3 in g_codes
        if ("K" in letters) != is_dwell:
            fail(path, expected_sequence, "K is required only and always with G04")
        if is_arc and not {"I", "J"}.issubset(letters):
            fail(path, expected_sequence, "G02/G03 requires both I and J")
        if ("I" in letters or "J" in letters) and not is_arc:
            fail(path, expected_sequence, "I/J is only valid with G02/G03")

    final_words = parse_words(path, len(lines), lines[-1][re.match(r"^N[0-9]+", lines[-1]).end():])
    final_m = {int(float(value)) for letter, value in final_words if letter == "M"}
    if not {2, 5}.issubset(final_m):
        fail(path, len(lines), "final block must contain M05 and M02")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} P123.TXT", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        validate(path)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"OK: {path} ({len(path.read_text(encoding='ascii').splitlines())} blocks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
