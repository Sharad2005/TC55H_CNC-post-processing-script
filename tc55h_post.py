"""FreeCAD CAM adapter for the TopCNC TC55H controller."""

from __future__ import annotations

import importlib.util
import math
import os
from pathlib import Path as FilePath
import sys
from typing import Dict, Iterable, Optional

import FreeCAD
from Path.Post.Processor import PostProcessor


def _load_core():
    core_path = FilePath(__file__).with_name("tc55h_core.py")
    spec = importlib.util.spec_from_file_location("tc55h_core", core_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {core_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


core = _load_core()

TOOLTIP = """TopCNC TC55H post for a CM45L/6040 XYZ router.

Writes uppercase P<number>.TXT files with at most 900 numbered blocks,
10:1 spindle scaling, and safe manually started continuation files.
Release 1.0.0; TC55H Baseline 1.0.
"""


def _code(name: object) -> str:
    text = str(name).strip().upper().replace(" ", "")
    if not text:
        return ""
    if text[0] in "GM" and text[1:].isdigit():
        return text[0] + str(int(text[1:]))
    return text


def _parameters(command: object) -> Dict[str, float]:
    raw = getattr(command, "Parameters", {}) or {}
    result: Dict[str, float] = {}
    for key, value in raw.items():
        letter = str(key).upper()
        if letter in {"A", "B", "C"}:
            raise core.TC55HError(f"Rotary axis {letter} is not supported")
        try:
            result[letter] = float(value)
        except (TypeError, ValueError):
            raise core.TC55HError(f"Invalid {letter} value in FreeCAD path") from None
    return result


def _feed(params: Dict[str, float]) -> Optional[float]:
    # FreeCAD Path.Command stores velocity in its internal mm/s unit.
    return params["F"] * 60.0 if "F" in params else None


def _centres_from_radius(
    start_u: float,
    start_v: float,
    end_u: float,
    end_v: float,
    radius_word: float,
    clockwise: bool,
) -> tuple[float, float]:
    chord_u = end_u - start_u
    chord_v = end_v - start_v
    chord = math.hypot(chord_u, chord_v)
    radius = abs(radius_word)
    if chord == 0 or chord > 2 * radius:
        raise core.TC55HError("Invalid radius-format arc")
    midpoint_u = (start_u + end_u) / 2.0
    midpoint_v = (start_v + end_v) / 2.0
    height = math.sqrt(max(0.0, radius * radius - (chord / 2.0) ** 2))
    side = -1.0 if clockwise else 1.0
    if radius_word < 0:
        side *= -1.0
    centre_u = midpoint_u - side * chord_v * height / chord
    centre_v = midpoint_v + side * chord_u * height / chord
    return centre_u - start_u, centre_v - start_v


class FreeCADAdapter:
    """Translate FreeCAD Path.Command objects into TC55H semantic events."""

    def __init__(self) -> None:
        self.builder = core.ProgramBuilder()
        self.plane = "G17"
        self.retract_mode = "G98"
        self.tools = set()
        self.pending_speed: Optional[float] = None
        self.cycle: Optional[str] = None
        self.cycle_values: Dict[str, float] = {}
        self.cycle_initial_z: Optional[float] = None

    def process_all(self, commands: Iterable[object]):
        for command in commands:
            self.process(command)
        return self.builder.finish()

    def _target(self, params: Dict[str, float]):
        current = self.builder.state.position
        return core.Position(
            params.get("X", current.x),
            params.get("Y", current.y),
            params.get("Z", current.z),
        )

    def _arc_offsets(
        self, params: Dict[str, float], target: "core.Position", clockwise: bool
    ) -> Dict[str, float]:
        pairs = {
            "G17": ("x", "y", "I", "J"),
            "G18": ("z", "x", "K", "I"),
            "G19": ("y", "z", "J", "K"),
        }
        u_name, v_name, u_word, v_word = pairs[self.plane]
        if u_word in params and v_word in params:
            return {u_word.lower(): params[u_word], v_word.lower(): params[v_word]}
        if "R" not in params:
            raise core.TC55HError("Arc requires I/J/K centre offsets or R")
        start = self.builder.state.position
        su, sv = getattr(start, u_name), getattr(start, v_name)
        eu, ev = getattr(target, u_name), getattr(target, v_name)
        if None in (su, sv, eu, ev):
            raise core.TC55HError("Radius-format arc requires a known start and end")
        du, dv = _centres_from_radius(su, sv, eu, ev, params["R"], clockwise)
        return {u_word.lower(): du, v_word.lower(): dv}

    def _drill(self, code: str, params: Dict[str, float]) -> None:
        if None in (
            self.builder.state.position.x,
            self.builder.state.position.y,
            self.builder.state.position.z,
        ):
            raise core.TC55HError("Drilling requires a known XYZ starting position")
        if self.cycle != code:
            self.cycle_initial_z = self.builder.state.position.z
        self.cycle = code
        self.cycle_values.update(params)
        values = self.cycle_values
        if "Z" not in values or "R" not in values:
            raise core.TC55HError(f"{code} requires Z and R")
        feed = _feed(values)
        if feed is None:
            feed = self.builder.state.feed
        core.validate_feed(feed)
        x = values.get("X", self.builder.state.position.x)
        y = values.get("Y", self.builder.state.position.y)
        self.builder.rapid(x=x, y=y)
        self.builder.rapid(z=values["R"])
        if code in {"G81", "G82"}:
            self.builder.linear(z=values["Z"], feed=feed)
            if code == "G82":
                dwell = values.get("P")
                if dwell is None:
                    raise core.TC55HError("G82 requires dwell P in seconds")
                self.builder.dwell(dwell)
        else:
            peck = values.get("Q")
            if peck is None or peck <= 0:
                raise core.TC55HError("G83 requires a positive Q peck depth")
            depth = values["R"]
            final_depth = values["Z"]
            if final_depth >= depth:
                raise core.TC55HError("G83 Z must be below its R plane")
            while depth > final_depth:
                depth = max(final_depth, depth - peck)
                self.builder.linear(z=depth, feed=feed)
                if depth > final_depth:
                    self.builder.rapid(z=values["R"])
        retract = values["R"]
        if self.retract_mode == "G98" and self.cycle_initial_z is not None:
            retract = max(retract, self.cycle_initial_z)
        self.builder.rapid(z=retract)

    def process(self, command: object) -> None:
        name = _code(getattr(command, "Name", ""))
        params = _parameters(command)
        if not name or name.startswith("(") or name == "COMMENT":
            return
        if name in {"G17", "G18", "G19"}:
            self.plane = name
            return
        if name in {"G21", "G40", "G49", "G80", "G90", "G94"}:
            if name == "G80":
                self.cycle = None
                self.cycle_values = {}
            return
        if name in {"G98", "G99"}:
            self.retract_mode = name
            return
        if name == "G54":
            return
        if name in {"G55", "G56", "G57", "G58", "G59"}:
            raise core.TC55HError("Only FreeCAD's default G54 fixture is supported")
        if name in {"G20", "G28", "G41", "G42", "G43", "G53", "G91", "G93", "G95"}:
            raise core.TC55HError(f"Unsupported unsafe command {name}")
        if name in {"M7", "M8", "M9"}:
            return
        if name == "M6":
            if "T" not in params:
                raise core.TC55HError("FreeCAD tool change has no tool number")
            self.tools.add(int(params["T"]))
            if len(self.tools) > 1:
                raise core.TC55HError("Only one physical tool is supported per file sequence")
            return
        if name in {"M3", "M4"}:
            speed = params.get("S", self.pending_speed)
            if speed is None:
                raise core.TC55HError("Spindle start requires S in physical RPM")
            self.pending_speed = speed
            self.builder.start_spindle(speed, clockwise=name == "M3")
            return
        if name == "M5":
            self.builder.stop_spindle()
            return
        if name == "M0":
            self.builder.pause()
            return
        if name in {"M2", "M30"}:
            return
        if name == "M1":
            raise core.TC55HError("Optional stop M1 is not supported")
        if name == "G4":
            seconds = params.get("P", params.get("K"))
            if seconds is None:
                raise core.TC55HError("Dwell requires P seconds")
            self.builder.dwell(seconds)
            return
        if name in {"G81", "G82", "G83"}:
            self._drill(name, params)
            return
        if name in {"G73", "G74", "G76", "G84", "G85", "G86", "G87", "G88", "G89"}:
            raise core.TC55HError(f"Unsupported drilling, tapping, or boring command {name}")
        if name in {"G0", "G1"}:
            if self.cycle and any(axis in params for axis in ("X", "Y", "Z")):
                self._drill(self.cycle, params)
                return
            if name == "G0":
                self.builder.rapid(params.get("X"), params.get("Y"), params.get("Z"))
            else:
                self.builder.linear(
                    params.get("X"), params.get("Y"), params.get("Z"), _feed(params)
                )
            return
        if name in {"G2", "G3"}:
            clockwise = name == "G2"
            target = self._target(params)
            offsets = self._arc_offsets(params, target, clockwise)
            feed = _feed(params)
            current = self.builder.state.position
            changing_z = core._different(target.z, current.z)
            if self.plane == "G17" and not changing_z:
                self.builder.arc_xy(
                    clockwise,
                    target.x,
                    target.y,
                    offsets["i"],
                    offsets["j"],
                    feed,
                )
            else:
                self.builder.linearize_arc(clockwise, self.plane, target, offsets, feed)
            return
        raise core.TC55HError(f"Unsupported FreeCAD command {name}")


class Tc55H(PostProcessor):
    """FreeCAD 1.1 post-processor entry point."""

    def __init__(self, job, *args, **kwargs):
        super().__init__(job, TOOLTIP, [], "Metric", *args, **kwargs)

    @property
    def tooltip(self):
        return self._tooltip

    def process_arguments(self):
        args = str(getattr(self._job, "PostProcessorArgs", "") or "").strip()
        if args:
            raise core.TC55HError("This safety-profile post accepts no custom arguments")
        return True, None

    def _commands(self):
        fixture_count = len(getattr(self._job, "Fixtures", []) or [])
        if fixture_count != 1:
            raise core.TC55HError("Exactly one FreeCAD fixture (the default G54) is required")
        for _partname, objects in self._buildPostList():
            for obj in objects:
                path = getattr(obj, "Path", None)
                for command in getattr(path, "Commands", []) or []:
                    yield command

    def process_postables(self):
        if bool(getattr(self._job, "SplitOutput", False)):
            raise core.TC55HError("Disable FreeCAD Split Output; this post manages continuation files")
        requested = os.path.abspath(os.path.expanduser(self._job.PostProcessorOutputFile))
        base_number, _ = core.parse_program_path(requested)
        programs = core.render_programs(FreeCADAdapter().process_all(self._commands()), base_number)
        output_dir = os.path.dirname(requested)
        if not os.path.isdir(output_dir):
            raise core.TC55HError("The selected output directory does not exist")
        paths = [os.path.join(output_dir, name) for name, _text in programs]
        collisions = [path for path in paths if os.path.exists(path)]
        if collisions:
            raise core.TC55HError(
                "Refusing to overwrite existing output: "
                + ", ".join(os.path.basename(path) for path in collisions)
            )
        created = []
        try:
            for path, (_name, text) in zip(paths, programs):
                with open(path, "x", encoding="ascii", newline="\n") as handle:
                    handle.write(text)
                created.append(path)
                FreeCAD.Console.PrintMessage(f"TC55H wrote {path}\n")
        except Exception:
            for path in created:
                try:
                    os.remove(path)
                except OSError:
                    pass
            raise
        # Returning None tells FreeCAD that this post wrote the sequence itself.
        return [("allitems", None)]
