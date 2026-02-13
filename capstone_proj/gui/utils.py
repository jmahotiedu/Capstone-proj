"""Utility helpers for the Capstone desktop control center."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TRAJECTORY_OPTIONS = ("static", "circle", "half_circle", "ellipse", "figure8", "line")
RIGHT_MODE_OPTIONS = ("same", "mirror")
ARM_MODE_OPTIONS = ("both", "left", "right")
TASK_TEMPLATES: dict[str, dict[str, Any]] = {
    "Circle Joint Sweep": {
        "trajectory": "circle",
        "amp_a": 0.30,
        "amp_b": 0.30,
        "frequency": 0.20,
        "joint_a": 0,
        "joint_b": 1,
        "right_mode": "mirror",
        "arm_mode": "both",
        "phase_offset": 0.0,
        "joint_offset": 0.0,
    },
    "Half Circle Reach": {
        "trajectory": "half_circle",
        "amp_a": 0.35,
        "amp_b": 0.20,
        "frequency": 0.15,
        "joint_a": 0,
        "joint_b": 2,
        "right_mode": "same",
        "arm_mode": "both",
        "phase_offset": 0.0,
        "joint_offset": 0.05,
    },
    "Ellipse Stability Probe": {
        "trajectory": "ellipse",
        "amp_a": 0.40,
        "amp_b": 0.18,
        "frequency": 0.25,
        "joint_a": 0,
        "joint_b": 1,
        "right_mode": "mirror",
        "arm_mode": "both",
        "phase_offset": 0.0,
        "joint_offset": 0.0,
    },
    "Figure8 Coordination": {
        "trajectory": "figure8",
        "amp_a": 0.25,
        "amp_b": 0.20,
        "frequency": 0.25,
        "joint_a": 1,
        "joint_b": 2,
        "right_mode": "same",
        "arm_mode": "both",
        "phase_offset": 1.57,
        "joint_offset": 0.0,
    },
    "Line Oscillation": {
        "trajectory": "line",
        "amp_a": 0.30,
        "amp_b": 0.0,
        "frequency": 0.30,
        "joint_a": 3,
        "joint_b": 4,
        "right_mode": "same",
        "arm_mode": "both",
        "phase_offset": 0.0,
        "joint_offset": 0.0,
    },
}


@dataclass(frozen=True)
class SafetyLimits:
    max_sim_seconds: float
    max_amplitude: float
    max_frequency: float

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_python_executable(root: Path | None = None, fallback: str | None = None) -> str:
    """
    Resolve the Python executable for repo tasks.

    Preference order:
    1. repo-local `.venv` interpreter
    2. provided fallback
    3. currently running interpreter
    """

    effective_root = root if root is not None else project_root()
    venv_python = effective_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    if fallback:
        return fallback
    return sys.executable


def build_simulation_command(
    python_executable: str,
    model: str,
    sim_seconds: float,
    joint_offset: float,
    trajectory: str,
    amp_a: float,
    amp_b: float,
    frequency: float,
    joint_a: int,
    joint_b: int,
    right_mode: str,
    arm_mode: str,
    phase_offset: float,
) -> list[str]:
    return [
        python_executable,
        "startup.py",
        "--model",
        model,
        "--sim-seconds",
        str(sim_seconds),
        "--joint-offset",
        str(joint_offset),
        "--trajectory",
        trajectory,
        "--amp-a",
        str(amp_a),
        "--amp-b",
        str(amp_b),
        "--frequency",
        str(frequency),
        "--joint-a",
        str(joint_a),
        "--joint-b",
        str(joint_b),
        "--right-mode",
        right_mode,
        "--arm-mode",
        arm_mode,
        "--phase-offset",
        str(phase_offset),
    ]


def parse_number_list(raw: str) -> list[float]:
    tokens = [token.strip() for token in raw.split(",")]
    values = [float(token) for token in tokens if token]
    if not values:
        raise ValueError("Expected at least one numeric value.")
    return values


def _shape_components(
    trajectory: str,
    t_sec: float,
    frequency_hz: float,
    amp_a: float,
    amp_b: float,
    phase_rad: float = 0.0,
) -> tuple[float, float]:
    if trajectory == "static" or frequency_hz <= 0:
        return 0.0, 0.0
    angle = (2.0 * math.pi * frequency_hz * t_sec) + phase_rad
    if trajectory == "circle":
        return amp_a * math.cos(angle), amp_a * math.sin(angle)
    if trajectory == "ellipse":
        return amp_a * math.cos(angle), amp_b * math.sin(angle)
    if trajectory == "figure8":
        return amp_a * math.sin(angle), amp_b * math.sin(2.0 * angle)
    if trajectory == "line":
        return amp_a * math.sin(angle), 0.0
    if trajectory == "half_circle":
        normalized = (angle / (2.0 * math.pi)) % 1.0
        u = 1.0 - abs((2.0 * normalized) - 1.0)
        theta = math.pi * u
        return amp_a * math.cos(theta), amp_b * math.sin(theta)
    raise ValueError(f"Unsupported trajectory: {trajectory}")


def trajectory_point(
    *,
    trajectory: str,
    t_sec: float,
    frequency: float,
    amp_a: float,
    amp_b: float,
    phase_offset: float = 0.0,
) -> tuple[float, float]:
    if trajectory not in TRAJECTORY_OPTIONS:
        raise ValueError(f"Unsupported trajectory: {trajectory}")
    return _shape_components(trajectory, t_sec, frequency, amp_a, amp_b, phase_offset)


def trajectory_samples(
    *,
    trajectory: str,
    amp_a: float,
    amp_b: float,
    frequency: float,
    duration_sec: float,
    points: int = 240,
    phase_offset: float = 0.0,
) -> tuple[list[float], list[float], list[float]]:
    if trajectory not in TRAJECTORY_OPTIONS:
        raise ValueError(f"Unsupported trajectory: {trajectory}")
    if duration_sec <= 0:
        raise ValueError("duration_sec must be > 0")
    if points < 2:
        raise ValueError("points must be >= 2")
    dt = duration_sec / float(points - 1)
    times: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    for idx in range(points):
        t_sec = idx * dt
        x, y = _shape_components(trajectory, t_sec, frequency, amp_a, amp_b, phase_offset)
        times.append(t_sec)
        xs.append(x)
        ys.append(y)
    return times, xs, ys


def load_json_object(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return dict(default or {})
        loaded = json.loads(content)
        if isinstance(loaded, dict):
            return loaded
        return dict(default or {})
    except Exception:
        return dict(default or {})


def save_json_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        loaded = json.loads(content)
        if isinstance(loaded, list):
            return [item for item in loaded if isinstance(item, dict)]
        return []
    except Exception:
        return []


def save_json_list(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def human_size(byte_count: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(byte_count)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{byte_count} B"
