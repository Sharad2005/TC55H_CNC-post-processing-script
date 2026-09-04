from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_tc55h_output import validate, validate_sequence


VALID_PROGRAM = """N1 G90 M03 S2400
N2 G00 X0 Y0
N3 Z5
N4 G01 Z-1 F300
N5 G02 X10 Y10 I0 J10 F800
N6 G03 I-10 J0
N7 G04 K0.5
N8 M05 M02
"""

FIRST_CONTINUATION_FILE = """N1 G90 M03 S1200
N2 G00 X0 Y0
N3 Z5
N4 G01 Z-2 F200
N5 X10 F800
N6 G00 Z5
N7 M05 M02
"""

SECOND_CONTINUATION_FILE = """N1 G90 M03 S1200
N2 G00 X10 Y0
N3 G01 Z-2 F200
N4 G01 X20 F800
N5 G00 Z5
N6 M05 M02
"""

NATURAL_FIRST_FILE = """N1 G90 M03 S1200
N2 G00 X0 Y0
N3 Z5
N4 G01 Z-2 F200
N5 G00 Z5
N6 M05 M02
"""

NATURAL_SECOND_FILE = """N1 G90 M03 S1200
N2 G00 X0 Y0
N3 G01 X10 Z-2 F800
N4 G00 Z5
N5 M05 M02
"""


class ValidatorTests(unittest.TestCase):
    def write_program(self, folder: str, filename: str, text: str) -> Path:
        path = Path(folder, filename)
        path.write_text(text, encoding="ascii")
        return path

    def validate_text(self, text: str, filename: str = "P123.TXT") -> None:
        with tempfile.TemporaryDirectory() as folder:
            validate(self.write_program(folder, filename, text))

    def assert_rejected(self, text: str, filename: str = "P123.TXT") -> None:
        with self.assertRaises(ValueError):
            self.validate_text(text, filename)

    def test_representative_program(self) -> None:
        self.validate_text(VALID_PROGRAM)

    def test_valid_continuation_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            first = self.write_program(folder, "P1.TXT", FIRST_CONTINUATION_FILE)
            second = self.write_program(folder, "P2.TXT", SECOND_CONTINUATION_FILE)
            validate_sequence([first, second])

    def test_valid_natural_clearance_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            first = self.write_program(folder, "P1.TXT", NATURAL_FIRST_FILE)
            second = self.write_program(folder, "P2.TXT", NATURAL_SECOND_FILE)
            validate_sequence([first, second])

    def test_rejects_wrong_sequence(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N2", "N3", 1))

    def test_rejects_unsafe_g_code(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N2 G00", "N2 G28", 1))

    def test_rejects_unscaled_spindle_command(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("S2400", "S24000", 1))

    def test_rejects_blank_line(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N4", "\nN4", 1))

    def test_rejects_missing_program_end(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("M05 M02", "M05", 1))

    def test_rejects_wrong_filename(self) -> None:
        self.assert_rejected(VALID_PROGRAM, "job.TXT")

    def test_rejects_lowercase_filename(self) -> None:
        self.assert_rejected(VALID_PROGRAM, "p123.txt")

    def test_rejects_padded_sequence(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N1 ", "N01 ", 1))

    def test_rejects_unpadded_g_code(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("G00", "G0", 1))

    def test_rejects_excess_coordinate_precision(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("X10", "X10.0001", 1))

    def test_rejects_extra_final_word(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("M05 M02", "G90 M05 M02", 1))

    def test_rejects_missing_spaces(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N1 G90", "N1G90", 1))

    def test_rejects_repeated_spaces(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N1 G90", "N1  G90", 1))

    def test_rejects_tabs(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N1 G90", "N1\tG90", 1))

    def test_rejects_nonconsecutive_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            first = self.write_program(folder, "P1.TXT", FIRST_CONTINUATION_FILE)
            third = self.write_program(folder, "P3.TXT", SECOND_CONTINUATION_FILE)
            with self.assertRaises(ValueError):
                validate_sequence([first, third])

    def test_rejects_bad_resume_z(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            first = self.write_program(folder, "P1.TXT", FIRST_CONTINUATION_FILE)
            second_text = SECOND_CONTINUATION_FILE.replace("Z-2 F200", "Z-1 F200", 1)
            second = self.write_program(folder, "P2.TXT", second_text)
            with self.assertRaises(ValueError):
                validate_sequence([first, second])

    def test_rejects_more_than_999_blocks(self) -> None:
        lines = [f"N{number} G00 X{number}" for number in range(1, 1000)]
        lines.append("N1000 M05 M02")
        self.assert_rejected("\n".join(lines) + "\n")


if __name__ == "__main__":
    unittest.main()
