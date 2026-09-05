"""CAM-independent TC55H event model, renderer, and continuation partitioner."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


BLOCK_LIMIT = 900
MAX_FILES = 99
SAFE_SPLIT_LOOKBACK = 100
MAX_PHYSICAL_SPINDLE_RPM = 24_000
SPINDLE_COMMAND_DIVISOR = 10
COORDINATE_LIMIT = 99_999.999
FEED_LIMIT = 99_999
TOLERANCE = 0.002
RELEASE_VERSION = "1.0.0"
OUTPUT_SPECIFICATION = "TC55H Baseline 1.0"


class TC55HError(ValueError):
    """Raised when CAM data cannot be represented safely for the TC55H."""


@dataclass
class Position:
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

    def copy(self) -> "Position":
        return Position(self.x, self.y, self.z)


@dataclass
class State:
    position: Position = field(default_factory=Position)
    feed: Optional[float] = None
    spindle_running: bool = False
    spindle_clockwise: bool = True
    spindle_command: Optional[int] = None
    safe_z: Optional[float] = None
    plunge_feed: Optional[float] = None

    def copy(self) -> "State":
        return State(
            position=self.position.copy(),
            feed=self.feed,
            spindle_running=self.spindle_running,
            spindle_clockwise=self.spindle_clockwise,
            spindle_command=self.spindle_command,
            safe_z=self.safe_z,
            plunge_feed=self.plunge_feed,
        )


@dataclass
class Event:
    kind: str
    data: Dict[str, object]
    after: State
    is_motion: bool = False


@dataclass
class Segment:
    events: List[Event]
    start_state: Optional[State]
    end_state: State
    final: bool


def _different(first: Optional[float], second: Optional[float]) -> bool:
    if first is None and second is None:
        return False
    if first is None or second is None:
        return True
    return format_decimal(first, 3) != format_decimal(second, 3)


def _round_positive(value: float) -> int:
    return int(math.floor(value + 0.5))


def format_decimal(value: float, decimals: int = 3) -> str:
    if not math.isfinite(value):
        raise TC55HError("Non-finite numeric value is not supported")
    rounded = round(float(value), decimals)
    if rounded == 0:
        rounded = 0.0
    text = f"{rounded:.{decimals}f}".rstrip("0").rstrip(".")
    return text or "0"


def format_feed(value: float) -> str:
    validate_feed(value)
    return str(_round_positive(value))


def spindle_command(physical_rpm: float) -> int:
    if not isinstance(physical_rpm, (int, float)) or not math.isfinite(physical_rpm):
        raise TC55HError("Spindle speed must be a finite number")
    if physical_rpm <= 0:
        raise TC55HError("Spindle speed must be greater than 0 RPM")
    if physical_rpm > MAX_PHYSICAL_SPINDLE_RPM:
        raise TC55HError("Spindle speed exceeds the 24000 RPM physical machine limit")
    command = _round_positive(physical_rpm / SPINDLE_COMMAND_DIVISOR)
    if command < 1:
        raise TC55HError("Spindle speed is too low after applying TC55H scaling")
    return command


def validate_coordinate(value: Optional[float], axis: str) -> None:
    if value is None:
        return
    if not math.isfinite(value) or abs(value) > COORDINATE_LIMIT:
        raise TC55HError(f"{axis} exceeds the TC55H coordinate range")


def validate_feed(value: Optional[float]) -> None:
    if value is None or not math.isfinite(value) or value <= 0 or value > FEED_LIMIT:
        raise TC55HError("Feed must be greater than 0 and no more than 99999 mm/min")


class ProgramBuilder:
    """Build a controller-independent event stream from one CAM job."""

    def __init__(self) -> None:
        self.events: List[Event] = []
        self.state = State()

    def _append(self, kind: str, is_motion: bool = False, **data: object) -> None:
        self.events.append(Event(kind, data, self.state.copy(), is_motion))

    def start_spindle(self, physical_rpm: float, clockwise: bool = True) -> None:
        command = spindle_command(physical_rpm)
        if self.state.spindle_running and self.state.spindle_clockwise != clockwise:
            self.stop_spindle()
        if not self.state.spindle_running:
            self.state.spindle_running = True
            self.state.spindle_clockwise = clockwise
            self.state.spindle_command = command
            self._append(
                "spindle_start",
                clockwise=clockwise,
                spindle_command=command,
                include_absolute=not self.events,
            )
        elif self.state.spindle_command != command:
            self.change_spindle_speed(physical_rpm)

    def change_spindle_speed(self, physical_rpm: float) -> None:
        command = spindle_command(physical_rpm)
        if self.state.spindle_command != command:
            self.state.spindle_command = command
            self._append("spindle_speed", spindle_command=command)

    def stop_spindle(self) -> None:
        if self.state.spindle_running:
            self.state.spindle_running = False
            self._append("spindle_stop")

    def rapid(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
    ) -> None:
        for value, axis in ((x, "X"), (y, "Y"), (z, "Z")):
            validate_coordinate(value, axis)

        horizontal_requested = x is not None or y is not None
        if self.state.position.z is None and horizontal_requested:
            if z is None:
                raise TC55HError(
                    "The first horizontal move has no clearance Z; add a safe initial Z rapid"
                )
            self.rapid(z=z)
            self.rapid(x=x, y=y, z=z)
            return

        target = Position(
            self.state.position.x if x is None else x,
            self.state.position.y if y is None else y,
            self.state.position.z if z is None else z,
        )
        if not any(
            _different(new, old)
            for new, old in zip(
                (target.x, target.y, target.z),
                (self.state.position.x, self.state.position.y, self.state.position.z),
            )
        ):
            return
        self.state.position = target
        if z is not None:
            self.state.safe_z = z if self.state.safe_z is None else max(self.state.safe_z, z)
        self._append("rapid", True, position=target.copy())

    def linear(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        feed: Optional[float] = None,
    ) -> None:
        if None in (self.state.position.x, self.state.position.y, self.state.position.z):
            raise TC55HError("Linear motion requires a known XYZ starting position")
        active_feed = self.state.feed if feed is None else feed
        validate_feed(active_feed)
        for value, axis in ((x, "X"), (y, "Y"), (z, "Z")):
            validate_coordinate(value, axis)
        target = Position(
            self.state.position.x if x is None else x,
            self.state.position.y if y is None else y,
            self.state.position.z if z is None else z,
        )
        if not any(
            _different(new, old)
            for new, old in zip(
                (target.x, target.y, target.z),
                (self.state.position.x, self.state.position.y, self.state.position.z),
            )
        ):
            self.state.feed = active_feed
            return
        if target.z is not None and self.state.position.z is not None and target.z < self.state.position.z:
            self.state.plunge_feed = active_feed
        self.state.position = target
        self.state.feed = active_feed
        self._append("linear", True, position=target.copy(), feed=active_feed)

    def arc_xy(
        self,
        clockwise: bool,
        x: Optional[float],
        y: Optional[float],
        i: float,
        j: float,
        feed: Optional[float] = None,
    ) -> None:
        if None in (self.state.position.x, self.state.position.y, self.state.position.z):
            raise TC55HError("Arc motion requires a known XYZ starting position")
        active_feed = self.state.feed if feed is None else feed
        validate_feed(active_feed)
        for value, axis in ((x, "X"), (y, "Y"), (i, "I"), (j, "J")):
            validate_coordinate(value, axis)
        target = Position(
            self.state.position.x if x is None else x,
            self.state.position.y if y is None else y,
            self.state.position.z,
        )
        full_circle = not _different(target.x, self.state.position.x) and not _different(
            target.y, self.state.position.y
        )
        self.state.position = target
        self.state.feed = active_feed
        self._append(
            "arc",
            True,
            clockwise=clockwise,
            position=target.copy(),
            i=i,
            j=j,
            feed=active_feed,
            full_circle=full_circle,
        )

    def linearize_arc(
        self,
        clockwise: bool,
        plane: str,
        end: Position,
        offsets: Dict[str, float],
        feed: Optional[float] = None,
    ) -> None:
        if None in (self.state.position.x, self.state.position.y, self.state.position.z):
            raise TC55HError("Arc linearization requires a known XYZ starting position")
        pairs = {
            "G17": ("x", "y", "i", "j", "z"),
            "G18": ("z", "x", "k", "i", "y"),
            "G19": ("y", "z", "j", "k", "x"),
        }
        if plane not in pairs:
            raise TC55HError(f"Unsupported arc plane {plane}")
        u_name, v_name, du_name, dv_name, w_name = pairs[plane]
        if du_name not in offsets or dv_name not in offsets:
            raise TC55HError("Arc linearization requires centre offsets")
        start = self.state.position.copy()
        su, sv = getattr(start, u_name), getattr(start, v_name)
        eu, ev = getattr(end, u_name), getattr(end, v_name)
        assert su is not None and sv is not None and eu is not None and ev is not None
        cu = su + offsets[du_name]
        cv = sv + offsets[dv_name]
        radius = math.hypot(su - cu, sv - cv)
        if radius <= TOLERANCE:
            raise TC55HError("Arc radius is too small")
        start_angle = math.atan2(sv - cv, su - cu)
        same_endpoint = not _different(su, eu) and not _different(sv, ev)
        if same_endpoint:
            sweep = -2 * math.pi if clockwise else 2 * math.pi
        else:
            end_angle = math.atan2(ev - cv, eu - cu)
            sweep = end_angle - start_angle
            if clockwise:
                while sweep >= 0:
                    sweep -= 2 * math.pi
            else:
                while sweep <= 0:
                    sweep += 2 * math.pi
        cosine = max(-1.0, min(1.0, 1.0 - TOLERANCE / radius))
        max_angle = max(0.001, 2 * math.acos(cosine))
        segments = max(1, int(math.ceil(abs(sweep) / max_angle)))
        start_w = getattr(start, w_name)
        end_w = getattr(end, w_name)
        assert start_w is not None and end_w is not None
        for index in range(1, segments + 1):
            ratio = index / segments
            angle = start_angle + sweep * ratio
            values = {
                u_name: eu if index == segments else cu + radius * math.cos(angle),
                v_name: ev if index == segments else cv + radius * math.sin(angle),
                w_name: end_w if index == segments else start_w + (end_w - start_w) * ratio,
            }
            self.linear(values.get("x"), values.get("y"), values.get("z"), feed)

    def dwell(self, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds < 0.001 or seconds > 99_999.999:
            raise TC55HError("TC55H dwell must be between 0.001 and 99999.999 seconds")
        self._append("dwell", seconds=seconds)

    def pause(self) -> None:
        self._append("pause")

    def finish(self) -> List[Event]:
        while self.events and self.events[-1].kind == "spindle_stop":
            self.events.pop()
        if not self.events or self.events[0].kind != "spindle_start":
            raise TC55HError("The job must start with one valid spindle command")
        if not any(event.is_motion for event in self.events):
            raise TC55HError("The job contains no supported motion")
        return list(self.events)


def _handoff_z(state: State) -> float:
    if state.position.z is None or state.safe_z is None:
        raise TC55HError("Cannot split before position and safe Z are known")
    return max(state.position.z, state.safe_z)


def _needs_retract(state: State) -> bool:
    return _different(_handoff_z(state), state.position.z)


def _can_handoff(state: State) -> bool:
    position = state.position
    if None in (position.x, position.y, position.z, state.safe_z):
        return False
    return not _needs_retract(state) or state.plunge_feed is not None or state.feed is not None


def _opening_count(state: State) -> int:
    count = 1
    if state.position.x is not None or state.position.y is not None:
        count += 1
    if _needs_retract(state):
        count += 1
    return count


def _ending_count(state: State) -> int:
    if state.position.z is None or state.safe_z is None:
        return 2
    return (1 if _needs_retract(state) else 0) + 1


def partition_events(events: Sequence[Event]) -> List[Segment]:
    segments: List[Segment] = []
    start = 0
    start_state: Optional[State] = None
    while start < len(events):
        opening = 0 if not segments else _opening_count(start_state)  # type: ignore[arg-type]
        maximum_end = start
        for end in range(start + 1, len(events) + 1):
            boundary = events[end - 1].after
            ending = 1 if end == len(events) else _ending_count(boundary)
            if opening + (end - start) + ending > BLOCK_LIMIT:
                break
            if end == len(events) or _can_handoff(boundary):
                maximum_end = end
        if maximum_end == start:
            raise TC55HError("Continuation overhead leaves no room for a machining block")
        chosen_end = maximum_end
        if maximum_end < len(events):
            earliest = max(start + 1, maximum_end - SAFE_SPLIT_LOOKBACK)
            for candidate in range(maximum_end, earliest - 1, -1):
                state = events[candidate - 1].after
                if (
                    events[candidate - 1].is_motion
                    and state.position.z is not None
                    and state.safe_z is not None
                    and not _different(max(state.position.z, state.safe_z), state.position.z)
                ):
                    chosen_end = candidate
                    break
        end_state = events[chosen_end - 1].after.copy()
        segments.append(
            Segment(
                events=list(events[start:chosen_end]),
                start_state=None if not segments else start_state.copy(),  # type: ignore[union-attr]
                end_state=end_state,
                final=chosen_end == len(events),
            )
        )
        start = chosen_end
        start_state = end_state.copy()
        if len(segments) > MAX_FILES:
            raise TC55HError("TC55H sequence exceeds the 99-file limit")
    return segments


@dataclass
class _RenderState:
    position: Position = field(default_factory=Position)
    motion: Optional[int] = None
    feed: Optional[float] = None
    force_motion: bool = False
    force_feed: bool = False


def _axis(letter: str, value: Optional[float]) -> str:
    return "" if value is None else letter + format_decimal(value)


def _line(number: int, words: Iterable[str]) -> str:
    filtered = [word for word in words if word]
    if not filtered:
        raise TC55HError("Attempted to create an empty TC55H block")
    return f"N{number} " + " ".join(filtered)


def _append_line(lines: List[str], words: Iterable[str]) -> None:
    if len(lines) >= BLOCK_LIMIT:
        raise TC55HError("Rendered continuation exceeds the 900-block limit")
    lines.append(_line(len(lines) + 1, words))


def _render_motion(event: Event, state: _RenderState) -> List[str]:
    motion = 0 if event.kind == "rapid" else 1 if event.kind == "linear" else 2 if event.data["clockwise"] else 3
    words: List[str] = []
    if state.force_motion or state.motion != motion:
        words.append(f"G{motion:02d}")
    position = event.data["position"]
    assert isinstance(position, Position)
    if event.kind == "arc":
        if not event.data["full_circle"]:
            if _different(position.x, state.position.x):
                words.append(_axis("X", position.x))
            if _different(position.y, state.position.y):
                words.append(_axis("Y", position.y))
        words.extend((_axis("I", float(event.data["i"])), _axis("J", float(event.data["j"]))))
        feed = float(event.data["feed"])
        if state.force_feed or format_feed(feed) != (format_feed(state.feed) if state.feed else None):
            words.append("F" + format_feed(feed))
    else:
        for letter, new, old in (
            ("X", position.x, state.position.x),
            ("Y", position.y, state.position.y),
            ("Z", position.z, state.position.z),
        ):
            if _different(new, old):
                words.append(_axis(letter, new))
        if event.kind == "linear":
            feed = float(event.data["feed"])
            if state.force_feed or format_feed(feed) != (format_feed(state.feed) if state.feed else None):
                words.append("F" + format_feed(feed))
    state.position = position.copy()
    state.motion = motion
    if "feed" in event.data:
        state.feed = float(event.data["feed"])
    state.force_motion = False
    state.force_feed = False
    return words


def _render_event(event: Event, state: _RenderState) -> List[str]:
    if event.kind in {"rapid", "linear", "arc"}:
        return _render_motion(event, state)
    if event.kind == "spindle_start":
        return [
            "G90" if event.data["include_absolute"] else "",
            "M03" if event.data["clockwise"] else "M04",
            "S" + str(event.data["spindle_command"]),
        ]
    if event.kind == "spindle_speed":
        return ["S" + str(event.data["spindle_command"])]
    if event.kind == "spindle_stop":
        return ["M05"]
    if event.kind == "pause":
        return ["M00"]
    if event.kind == "dwell":
        return ["G04", "K" + format_decimal(float(event.data["seconds"]))]
    raise TC55HError(f"Unknown event type {event.kind}")


def render_segment(segment: Segment, index: int) -> List[str]:
    lines: List[str] = []
    state = _RenderState()
    if index:
        saved = segment.start_state
        assert saved is not None
        opening = ["G90"]
        if saved.spindle_running:
            opening.extend(
                ("M03" if saved.spindle_clockwise else "M04", f"S{saved.spindle_command}")
            )
        _append_line(lines, opening)
        handoff_z = _handoff_z(saved)
        if saved.position.x is not None or saved.position.y is not None:
            _append_line(lines, ["G00", _axis("X", saved.position.x), _axis("Y", saved.position.y)])
        if _different(handoff_z, saved.position.z):
            resume_feed = saved.plunge_feed if saved.plunge_feed is not None else saved.feed
            validate_feed(resume_feed)
            _append_line(lines, ["G01", _axis("Z", saved.position.z), "F" + format_feed(resume_feed)])
            state.motion = 1
            state.feed = resume_feed
        else:
            state.motion = 0
        state.position = saved.position.copy()
        state.force_motion = True
        state.force_feed = True
    for event in segment.events:
        _append_line(lines, _render_event(event, state))
    if segment.final:
        _append_line(lines, ["M05", "M02"])
    else:
        handoff_z = _handoff_z(segment.end_state)
        if _different(handoff_z, segment.end_state.position.z):
            _append_line(lines, ["G00", _axis("Z", handoff_z)])
        _append_line(lines, ["M05", "M02"])
    return lines


def render_programs(events: Sequence[Event], base_number: int) -> List[Tuple[str, str]]:
    if base_number < 0 or base_number > 9999:
        raise TC55HError("Program number must contain 1 to 4 digits")
    segments = partition_events(events)
    if base_number + len(segments) - 1 > 9999:
        raise TC55HError("Continuation filenames would exceed P9999.TXT")
    programs: List[Tuple[str, str]] = []
    for index, segment in enumerate(segments):
        name = f"P{base_number + index}.TXT"
        programs.append((name, "\n".join(render_segment(segment, index)) + "\n"))
    return programs


def parse_program_path(path: str) -> Tuple[int, str]:
    match = re.fullmatch(r"P([0-9]{1,4})\.TXT", os.path.basename(path))
    if not match:
        raise TC55HError("Output filename must be uppercase P plus 1-4 digits and .TXT")
    return int(match.group(1)), match.group(0)
