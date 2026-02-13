import tempfile
import unittest
from pathlib import Path

from capstone_proj.gui.utils import build_simulation_command, resolve_python_executable


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


if __name__ == "__main__":
    unittest.main()
