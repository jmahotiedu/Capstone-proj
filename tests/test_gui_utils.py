import tempfile
import unittest
from pathlib import Path

from capstone_proj.gui.utils import (
    build_simulation_command,
    human_size,
    parse_number_list,
    resolve_python_executable,
    trajectory_samples,
)


class GuiUtilsTest(unittest.TestCase):
    def test_build_simulation_command(self):
        cmd = build_simulation_command(
            python_executable="python.exe",
            model="aloha.xml",
            sim_seconds=30.0,
            joint_offset=0.25,
            trajectory="ellipse",
            amp_a=0.30,
            amp_b=0.20,
            frequency=0.50,
            joint_a=0,
            joint_b=1,
            right_mode="mirror",
            phase_offset=1.57,
        )

        self.assertEqual(
            cmd,
            [
                "python.exe",
                "startup.py",
                "--model",
                "aloha.xml",
                "--sim-seconds",
                "30.0",
                "--joint-offset",
                "0.25",
                "--trajectory",
                "ellipse",
                "--amp-a",
                "0.3",
                "--amp-b",
                "0.2",
                "--frequency",
                "0.5",
                "--joint-a",
                "0",
                "--joint-b",
                "1",
                "--right-mode",
                "mirror",
                "--phase-offset",
                "1.57",
            ],
        )

    def test_resolve_python_executable_prefers_repo_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv_python = root / ".venv" / "Scripts" / "python.exe"
            venv_python.parent.mkdir(parents=True, exist_ok=True)
            venv_python.write_text("")

            resolved = resolve_python_executable(root=root, fallback="fallback-python")
            self.assertEqual(resolved, str(venv_python))

    def test_resolve_python_executable_uses_fallback_when_no_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolved = resolve_python_executable(root=root, fallback="fallback-python")
            self.assertEqual(resolved, "fallback-python")

    def test_parse_number_list(self):
        values = parse_number_list("0.1, 0.2,1.0")
        self.assertEqual(values, [0.1, 0.2, 1.0])

    def test_trajectory_samples_returns_requested_points(self):
        times, xs, ys = trajectory_samples(
            trajectory="ellipse",
            amp_a=0.3,
            amp_b=0.2,
            frequency=0.2,
            duration_sec=5.0,
            points=120,
        )
        self.assertEqual(len(times), 120)
        self.assertEqual(len(xs), 120)
        self.assertEqual(len(ys), 120)

    def test_human_size(self):
        self.assertEqual(human_size(512), "512.0 B")
        self.assertEqual(human_size(2048), "2.0 KB")


if __name__ == "__main__":
    unittest.main()
