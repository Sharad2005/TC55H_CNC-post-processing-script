import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import tc55h_core as core
from validate_tc55h_output import validate_sequence


class TC55HCoreTests(unittest.TestCase):
    def basic_builder(self):
        builder = core.ProgramBuilder()
        builder.start_spindle(24000)
        builder.rapid(z=5)
        builder.rapid(x=0, y=0)
        return builder

    def test_spindle_scaling(self):
        self.assertEqual(core.spindle_command(6000), 600)
        self.assertEqual(core.spindle_command(12000), 1200)
        self.assertEqual(core.spindle_command(18000), 1800)
        self.assertEqual(core.spindle_command(24000), 2400)
        self.assertEqual(core.spindle_command(12345), 1235)
        for speed in (0, -1, 24001):
            with self.assertRaises(core.TC55HError):
                core.spindle_command(speed)

    def test_initial_clearance_and_exact_format(self):
        builder = core.ProgramBuilder()
        builder.start_spindle(12000)
        builder.rapid(x=10, y=20, z=5)
        builder.linear(z=-1, feed=200)
        programs = core.render_programs(builder.finish(), 1)
        self.assertEqual(programs[0][0], "P1.TXT")
        self.assertEqual(
            programs[0][1].splitlines(),
            [
                "N1 G90 M03 S1200",
                "N2 G00 Z5",
                "N3 X10 Y20",
                "N4 G01 Z-1 F200",
                "N5 M05 M02",
            ],
        )

    def test_xy_arc_is_preserved(self):
        builder = self.basic_builder()
        builder.linear(z=-1, feed=300)
        builder.arc_xy(False, 10, 0, 5, 0, 600)
        text = core.render_programs(builder.finish(), 3)[0][1]
        self.assertIn("G03 X10 I5 J0 F600", text)

    def test_helical_arc_is_linearized(self):
        builder = self.basic_builder()
        builder.linear(z=0, feed=300)
        builder.linearize_arc(
            False,
            "G17",
            core.Position(10, 0, -1),
            {"i": 5, "j": 0},
            500,
        )
        text = core.render_programs(builder.finish(), 4)[0][1]
        self.assertNotRegex(text, r" G0[23](?: |\n)")
        self.assertIn("G01", text)

    def test_901_event_job_splits_and_resumes(self):
        builder = self.basic_builder()
        builder.linear(z=-1, feed=200)
        for index in range(1, 910):
            builder.linear(x=index / 10, feed=800)
        programs = core.render_programs(builder.finish(), 8)
        self.assertEqual([name for name, _ in programs], ["P8.TXT", "P9.TXT"])
        self.assertTrue(all(len(text.splitlines()) <= 900 for _, text in programs))
        second = programs[1][1].splitlines()
        self.assertEqual(second[0], "N1 G90 M03 S2400")
        self.assertRegex(second[1], r"^N2 G00 X[-0-9.]+ Y0$")
        self.assertEqual(second[2], "N3 G01 Z-1 F200")
        for _name, text in programs:
            for number, line in enumerate(text.splitlines(), 1):
                self.assertTrue(line.startswith(f"N{number} "))
                self.assertIsNotNone(re.fullmatch(r"[A-Z0-9. -]+", line))
                self.assertNotIn("  ", line)
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, text in programs:
                path = Path(directory, name)
                path.write_text(text, encoding="ascii")
                paths.append(path)
            validate_sequence(paths)

    def test_filename_rules(self):
        self.assertEqual(core.parse_program_path("/tmp/P99.TXT"), (99, "P99.TXT"))
        for name in ("p1.TXT", "P1.txt", "1001.TXT", "P12345.TXT"):
            with self.assertRaises(core.TC55HError):
                core.parse_program_path(name)


if __name__ == "__main__":
    unittest.main()
