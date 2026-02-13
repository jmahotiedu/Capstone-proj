"""Utility helpers for the Capstone desktop control center."""

from __future__ import annotations

import sys
from pathlib import Path


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
        "--phase-offset",
        str(phase_offset),
    ]
