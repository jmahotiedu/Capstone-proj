"""CLI runner for the baseline MuJoCo PID simulation."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

from capstone_proj.control import JointSpacePDController


def _demo_targets(joint_offset: float) -> tuple[np.ndarray, np.ndarray]:
    q_des_left = np.zeros(7, dtype=float)
    q_des_right = np.zeros(7, dtype=float)
    q_des_left[0] = joint_offset
    q_des_right[0] = joint_offset
    return q_des_left, q_des_right


def run_simulation(model_path: Path, sim_seconds: float, joint_offset: float) -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    controller = JointSpacePDController(model)
    q_des_left, q_des_right = _demo_targets(joint_offset)

    dt = float(model.opt.timestep)
    steps = max(1, int(sim_seconds / dt))

    with mujoco.viewer.launch_passive(model, data) as viewer:
        for _ in range(steps):
            if not viewer.is_running():
                break
            tau = controller.compute(data, q_des_left, q_des_right)
            data.ctrl[:] = tau
            mujoco.mj_step(model, data)
            viewer.sync()
            time.sleep(dt)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline ALOHA-like PID simulation.")
    parser.add_argument("--model", default="aloha.xml", help="Path to MuJoCo XML model.")
    parser.add_argument("--sim-seconds", type=float, default=60.0, help="Simulation duration in seconds.")
    parser.add_argument("--joint-offset", type=float, default=0.3, help="Demo offset for shoulder joint.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    model_path = Path(args.model).expanduser()
    if not model_path.is_absolute():
        model_path = Path.cwd() / model_path
    if not model_path.exists():
        raise FileNotFoundError(f"Model file does not exist: {model_path}")

    run_simulation(model_path=model_path, sim_seconds=args.sim_seconds, joint_offset=args.joint_offset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

