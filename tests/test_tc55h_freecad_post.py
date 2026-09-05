import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path as FilePath

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from validate_tc55h_output import validate


class BasePost:
    def __init__(self, job, tooltip, tooltipargs, units, *args, **kwargs):
        self._job = job
        self._tooltip = tooltip
        self._units = units


freecad = types.ModuleType("FreeCAD")
freecad.Console = types.SimpleNamespace(PrintMessage=lambda message: None)
sys.modules.setdefault("FreeCAD", freecad)
path_module = types.ModuleType("Path")
path_module.__path__ = []
sys.modules.setdefault("Path", path_module)
post_module = types.ModuleType("Path.Post")
post_module.__path__ = []
sys.modules.setdefault("Path.Post", post_module)
processor_module = types.ModuleType("Path.Post.Processor")
processor_module.PostProcessor = BasePost
sys.modules.setdefault("Path.Post.Processor", processor_module)

spec = importlib.util.spec_from_file_location("tc55h_post", os.path.join(ROOT, "tc55h_post.py"))
post = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = post
spec.loader.exec_module(post)


class Command:
    def __init__(self, name, **parameters):
        self.Name = name
        self.Parameters = parameters


class FakePath:
    def __init__(self, commands):
        self.Commands = commands


class FakeObject:
    def __init__(self, commands):
        self.Path = FakePath(commands)


def simple_commands():
    return [
        Command("G54"),
        Command("M6", T=1),
        Command("M3", S=24000),
        Command("G0", Z=5),
        Command("G0", X=0, Y=0),
        Command("G1", Z=-1, F=5),
        Command("G2", X=10, Y=0, I=5, J=0, F=10),
        Command("M5"),
        Command("M30"),
    ]


class FreeCADAdapterTests(unittest.TestCase):
    def test_simple_path_and_internal_feed_conversion(self):
        events = post.FreeCADAdapter().process_all(simple_commands())
        text = post.core.render_programs(events, 1)[0][1]
        self.assertIn("N1 G90 M03 S2400", text)
        self.assertIn("G01 Z-1 F300", text)
        self.assertIn("G02 X10 I5 J0 F600", text)
        self.assertTrue(text.endswith("M05 M02\n"))

    def test_r_arc_and_helical_arc(self):
        commands = simple_commands()[:6] + [Command("G3", X=10, Y=0, Z=-2, R=5, F=10)]
        events = post.FreeCADAdapter().process_all(commands)
        text = post.core.render_programs(events, 2)[0][1]
        self.assertNotIn("G03", text)

    def test_drilling_cycle_expansion(self):
        commands = simple_commands()[:5] + [
            Command("G81", X=2, Y=3, Z=-4, R=1, F=2),
            Command("G80"),
        ]
        events = post.FreeCADAdapter().process_all(commands)
        text = post.core.render_programs(events, 3)[0][1]
        self.assertIn("X2 Y3", text)
        self.assertIn("Z-4 F120", text)
        self.assertNotIn("G81", text)

    def test_peck_cycle_never_rapids_down_into_hole(self):
        commands = simple_commands()[:5] + [
            Command("G83", X=2, Y=3, Z=-5, R=1, Q=2, F=2),
            Command("G80"),
        ]
        events = post.FreeCADAdapter().process_all(commands)
        text = post.core.render_programs(events, 4)[0][1]
        rapid_z = [line for line in text.splitlines() if "G00 Z" in line]
        self.assertTrue(all("Z-" not in line for line in rapid_z))

    def test_rotary_incremental_and_tapping_are_rejected(self):
        for command in (
            Command("G0", A=1),
            Command("G91"),
            Command("G84", Z=-5, R=1, F=2),
        ):
            with self.assertRaises(post.core.TC55HError):
                post.FreeCADAdapter().process(command)

    def test_multiple_tools_and_nondefault_fixture_rejected(self):
        adapter = post.FreeCADAdapter()
        adapter.process(Command("M6", T=1))
        with self.assertRaises(post.core.TC55HError):
            adapter.process(Command("M6", T=2))
        with self.assertRaises(post.core.TC55HError):
            post.FreeCADAdapter().process(Command("G55"))

    def test_post_writes_files_itself_and_refuses_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            job = types.SimpleNamespace(
                PostProcessorArgs="",
                PostProcessorOutputFile=os.path.join(directory, "P20.TXT"),
                SplitOutput=False,
                Fixtures=["G54"],
            )
            processor = post.Tc55H(job)
            processor._buildPostList = lambda: [("G54", [FakeObject(simple_commands())])]
            self.assertEqual(processor.process_postables(), [("allitems", None)])
            path = os.path.join(directory, "P20.TXT")
            self.assertTrue(os.path.isfile(path))
            validate(FilePath(path))
            with self.assertRaises(post.core.TC55HError):
                processor.process_postables()


if __name__ == "__main__":
    unittest.main()
