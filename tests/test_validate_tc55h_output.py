from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_tc55h_output import validate


VALID_PROGRAM = """N1G90M03S2400
N2G00X0Y0
N3Z5
N4G01Z-1F300
N5G02X10Y10I0J10F800
N6G03I-10J0
N7G04K0.5
N8M05M02
"""


class ValidatorTests(unittest.TestCase):
    def validate_text(self, text: str, filename: str = "P123.TXT") -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, filename)
            path.write_text(text, encoding="ascii")
            validate(path)

    def assert_rejected(self, text: str, filename: str = "P123.TXT") -> None:
        with self.assertRaises(ValueError):
            self.validate_text(text, filename)

    def test_representative_program(self) -> None:
        self.validate_text(VALID_PROGRAM)

    def test_rejects_wrong_sequence(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N2", "N3", 1))

    def test_rejects_unsafe_g_code(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N2G00", "N2G28", 1))

    def test_rejects_unscaled_spindle_command(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("S2400", "S24000", 1))

    def test_rejects_blank_line(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("N4", "\nN4", 1))

    def test_rejects_missing_program_end(self) -> None:
        self.assert_rejected(VALID_PROGRAM.replace("M05M02", "M05", 1))

    def test_rejects_wrong_filename(self) -> None:
        self.assert_rejected(VALID_PROGRAM, "job.TXT")

    def test_rejects_more_than_999_blocks(self) -> None:
        lines = [f"N{number}G00X{number}" for number in range(1, 1000)]
        lines.append("N1000M05M02")
        self.assert_rejected("\n".join(lines) + "\n")


if __name__ == "__main__":
    unittest.main()
