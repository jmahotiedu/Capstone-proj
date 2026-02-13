"""CLI runner for the baseline MuJoCo PID simulation."""

from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

from capstone_proj.control import JointSpacePDController


TRAJECTORY_CHOICES = ("static", "circle", "half_circle", "ellipse", "figure8", "line")
RIGHT_MODE_CHOICES = ("same", "mirror")


def _shape_components(
    trajectory: str,
    t_sec: float,
    frequency_hz: float,
    amp_a: float,
    amp_b: float,
    phase_rad: float,
) -> tuple[float, float]:
    if trajectory == "static" or frequency_hz <= 0.0:
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


def compute_desired_targets(
    *,
    base_left: np.ndarray,
    base_right: np.ndarray,
    t_sec: float,
    trajectory: str,
    joint_offset: float,
    amp_a: float,
    amp_b: float,
    frequency_hz: float,
    joint_a: int,
    joint_b: int,
    right_mode: str,
    phase_offset_rad: float,
) -> tuple[np.ndarray, np.ndarray]:
    if trajectory not in TRAJECTORY_CHOICES:
        raise ValueError(f"Unsupported trajectory: {trajectory}")
    if right_mode not in RIGHT_MODE_CHOICES:
        raise ValueError(f"Unsupported right_mode: {right_mode}")
    if not 0 <= joint_a <= 6 or not 0 <= joint_b <= 6:
        raise ValueError("joint_a and joint_b must be in [0, 6]")

    q_des_left = np.asarray(base_left, dtype=float).copy()
    q_des_right = np.asarray(base_right, dtype=float).copy()

    if q_des_left.shape != (7,) or q_des_right.shape != (7,):
        raise ValueError("base_left and base_right must have shape (7,)")

    if trajectory == "static":
        q_des_left[joint_a] += joint_offset
        q_des_right[joint_a] += joint_offset
        return q_des_left, q_des_right

    left_x, left_y = _shape_components(trajectory, t_sec, frequency_hz, amp_a, amp_b, phase_rad=0.0)
    right_x, right_y = _shape_components(
        trajectory,
        t_sec,
        frequency_hz,
        amp_a,
        amp_b,
        phase_rad=phase_offset_rad,
    )

    if right_mode == "mirror":
        right_x = -right_x

    q_des_left[joint_a] += joint_offset + left_x
    q_des_left[joint_b] += left_y
    q_des_right[joint_a] += joint_offset + right_x
    q_des_right[joint_b] += right_y
    return q_des_left, q_des_right


def run_simulation(
    model_path: Path,
    sim_seconds: float,
    joint_offset: float,
    trajectory: str,
    amp_a: float,
    amp_b: float,
    frequency_hz: float,
    joint_a: int,
    joint_b: int,
    right_mode: str,
    phase_offset_rad: float,
) -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    controller = JointSpacePDController(model)
    base_left = np.asarray(data.qpos[:7], dtype=float).copy()
    base_right = np.asarray(data.qpos[7:14], dtype=float).copy()

    dt = float(model.opt.timestep)
    steps = max(1, int(sim_seconds / dt))

    with mujoco.viewer.launch_passive(model, data) as viewer:
        for step in range(steps):
            if not viewer.is_running():
                break
            t_sec = step * dt
            q_des_left, q_des_right = compute_desired_targets(
                base_left=base_left,
                base_right=base_right,
                t_sec=t_sec,
                trajectory=trajectory,
                joint_offset=joint_offset,
                amp_a=amp_a,
                amp_b=amp_b,
                frequency_hz=frequency_hz,
                joint_a=joint_a,
                joint_b=joint_b,
                right_mode=right_mode,
                phase_offset_rad=phase_offset_rad,
            )
            tau = controller.compute(data, q_des_left, q_des_right)
            data.ctrl[:] = tau
            mujoco.mj_step(model, data)
            viewer.sync()
            time.sleep(dt)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline ALOHA-like PID simulation.")
    parser.add_argument("--model", default="aloha.xml", help="Path to MuJoCo XML model.")
    parser.add_argument("--sim-seconds", type=float, default=60.0, help="Simulation duration in seconds.")
    parser.add_argument("--joint-offset", type=float, default=0.3, help="Base offset applied on joint-a (radians).")
    parser.add_argument(
        "--trajectory",
        default="static",
        choices=TRAJECTORY_CHOICES,
        help="Joint-space geometry profile to run.",
    )
    parser.add_argument("--amp-a", type=float, default=0.30, help="Primary trajectory amplitude in radians.")
    parser.add_argument("--amp-b", type=float, default=0.20, help="Secondary trajectory amplitude in radians.")
    parser.add_argument("--frequency", type=float, default=0.20, help="Trajectory frequency in Hz.")
    parser.add_argument("--joint-a", type=int, default=0, help="First joint index for trajectory plane (0-6).")
    parser.add_argument("--joint-b", type=int, default=1, help="Second joint index for trajectory plane (0-6).")
    parser.add_argument(
        "--right-mode",
        default="same",
        choices=RIGHT_MODE_CHOICES,
        help="Right arm behavior relative to left trajectory.",
    )
    parser.add_argument("--phase-offset", type=float, default=0.0, help="Right-arm phase offset in radians.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    model_path = Path(args.model).expanduser()
    if not model_path.is_absolute():
        model_path = Path.cwd() / model_path
    if not model_path.exists():
        raise FileNotFoundError(f"Model file does not exist: {model_path}")
    if args.sim_seconds <= 0:
        raise ValueError("--sim-seconds must be > 0")
    if args.frequency < 0:
        raise ValueError("--frequency must be >= 0")
    if args.amp_a < 0 or args.amp_b < 0:
        raise ValueError("--amp-a and --amp-b must be >= 0")
    if not 0 <= args.joint_a <= 6 or not 0 <= args.joint_b <= 6:
        raise ValueError("--joint-a and --joint-b must be in [0, 6]")

    run_simulation(
        model_path=model_path,
        sim_seconds=args.sim_seconds,
        joint_offset=args.joint_offset,
        trajectory=args.trajectory,
        amp_a=args.amp_a,
        amp_b=args.amp_b,
        frequency_hz=args.frequency,
        joint_a=args.joint_a,
        joint_b=args.joint_b,
        right_mode=args.right_mode,
        phase_offset_rad=args.phase_offset,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
