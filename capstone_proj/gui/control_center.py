"""Tkinter desktop app to run common project tasks without terminal commands."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .feature_hub import FeatureHubWindow
from .utils import (
    ARM_MODE_OPTIONS,
    RIGHT_MODE_OPTIONS,
    TRAJECTORY_OPTIONS,
    build_simulation_command,
    load_json_list,
    project_root,
    resolve_python_executable,
    save_json_list,
)


class CapstoneControlCenter(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Capstone Control Center")
        self.geometry("1220x760")
        self.minsize(1080, 680)

        self.root_dir = project_root()
        self.log_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._active_process: subprocess.Popen[str] | None = None
        self._command_lock = threading.Lock()
        self._command_buttons: list[ttk.Button] = []

        self.model_var = tk.StringVar(value="aloha.xml")
        self.sim_seconds_var = tk.StringVar(value="60")
        self.joint_offset_var = tk.StringVar(value="0.3")
        self.trajectory_var = tk.StringVar(value="static")
        self.amp_a_var = tk.StringVar(value="0.30")
        self.amp_b_var = tk.StringVar(value="0.20")
        self.frequency_var = tk.StringVar(value="0.20")
        self.joint_a_var = tk.StringVar(value="0")
        self.joint_b_var = tk.StringVar(value="1")
        self.right_mode_var = tk.StringVar(value="same")
        self.arm_mode_var = tk.StringVar(value="both")
        self.phase_offset_var = tk.StringVar(value="0.0")
        self.python_var = tk.StringVar(value=resolve_python_executable(self.root_dir))
        self.status_var = tk.StringVar(value="Idle")
        self.record_runs_var = tk.BooleanVar(value=True)
        self.auto_report_var = tk.BooleanVar(value=True)
        self.safety_max_seconds_var = tk.StringVar(value="600")
        self.safety_max_amplitude_var = tk.StringVar(value="1.2")
        self.safety_max_frequency_var = tk.StringVar(value="1.5")

        self.run_records_path = self.root_dir / "artifacts" / "gui_runs.json"
        self.run_reports_dir = self.root_dir / "artifacts" / "reports"
        self.run_records: list[dict] = load_json_list(self.run_records_path)
        self.session_events: list[dict] = []
        self._next_run_id = self._infer_next_run_id()
        self._feature_hub_window: FeatureHubWindow | None = None
        self._sweep_queue: list[dict] = []
        self._pending_command_metadata: dict | None = None

        self._resource_paths = [
            "README.md",
            "CONTRIBUTING.md",
            "aloha.xml",
            "joint_position_actuators.xml",
            "keyframe_ctrl.xml",
            "configs/experiment-template.json",
            "docs/research/reading-list.md",
            "docs/roadmap/semester-plan.md",
            "docs/experiments/pi0-groot-baseline-plan.md",
            "docs/ops/failure-intervention.md",
            "tests/test_pid_controller.py",
            "capstone_proj/control/pid_controller.py",
            "capstone_proj/simulation/run_pid.py",
        ]

        self._build_layout()
        self._refresh_environment()
        self.add_timeline_event("Control Center started.")
        self.after(120, self._drain_queue)

    def _infer_next_run_id(self) -> int:
        highest = 0
        for record in self.run_records:
            raw = str(record.get("id", ""))
            if raw.startswith("run-"):
                try:
                    highest = max(highest, int(raw.split("-")[-1]))
                except ValueError:
                    continue
        return highest + 1

    def add_timeline_event(self, message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.session_events.append({"timestamp": stamp, "message": message})
        if len(self.session_events) > 600:
            self.session_events = self.session_events[-600:]

    def _save_run_records(self) -> None:
        save_json_list(self.run_records_path, self.run_records)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header, text="Capstone Control Center", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            header,
            text="Run tests/simulation, inspect git status, and open docs without terminal commands.",
        ).pack(anchor=tk.W, pady=(2, 0))

        splitter = ttk.Panedwindow(container, orient=tk.HORIZONTAL)
        splitter.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(splitter, padding=(0, 0, 10, 0))
        right = ttk.Frame(splitter)
        splitter.add(left, weight=1)
        splitter.add(right, weight=2)

        self._build_controls(left)
        self._build_log_panel(right)

    def _build_controls(self, parent: ttk.Frame) -> None:
        env_frame = ttk.LabelFrame(parent, text="Environment", padding=10)
        env_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(env_frame, text="Repository").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(env_frame, text=str(self.root_dir), wraplength=420).grid(row=1, column=0, sticky=tk.W, pady=(0, 6))

        ttk.Label(env_frame, text="Python").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(env_frame, textvariable=self.python_var, state="readonly").grid(row=3, column=0, sticky=tk.EW)

        env_buttons = ttk.Frame(env_frame)
        env_buttons.grid(row=4, column=0, sticky=tk.W, pady=(8, 0))

        refresh_btn = ttk.Button(env_buttons, text="Refresh Env", command=self._refresh_environment)
        refresh_btn.pack(side=tk.LEFT)
        create_venv_btn = ttk.Button(env_buttons, text="Create .venv", command=self._create_venv)
        create_venv_btn.pack(side=tk.LEFT, padx=(8, 0))
        install_btn = ttk.Button(env_buttons, text="Install Requirements", command=self._install_requirements)
        install_btn.pack(side=tk.LEFT, padx=(8, 0))

        self._command_buttons.extend([refresh_btn, create_venv_btn, install_btn])
        env_frame.columnconfigure(0, weight=1)

        sim_frame = ttk.LabelFrame(parent, text="Simulation", padding=10)
        sim_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(sim_frame, text="Model XML").grid(row=0, column=0, sticky=tk.W)
        model_entry = ttk.Entry(sim_frame, textvariable=self.model_var)
        model_entry.grid(row=1, column=0, sticky=tk.EW)
        ttk.Button(sim_frame, text="Browse", command=self._browse_model).grid(row=1, column=1, padx=(8, 0))

        ttk.Label(sim_frame, text="Simulation Seconds").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(sim_frame, textvariable=self.sim_seconds_var).grid(row=3, column=0, sticky=tk.EW)

        ttk.Label(sim_frame, text="Base Joint Offset (rad)").grid(row=4, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(sim_frame, textvariable=self.joint_offset_var).grid(row=5, column=0, sticky=tk.EW)

        ttk.Label(sim_frame, text="Trajectory").grid(row=6, column=0, sticky=tk.W, pady=(8, 0))
        trajectory_box = ttk.Combobox(
            sim_frame,
            textvariable=self.trajectory_var,
            values=TRAJECTORY_OPTIONS,
            state="readonly",
        )
        trajectory_box.grid(row=7, column=0, sticky=tk.EW)

        ttk.Label(sim_frame, text="Amplitude A (rad)").grid(row=8, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(sim_frame, textvariable=self.amp_a_var).grid(row=9, column=0, sticky=tk.EW)
        ttk.Label(sim_frame, text="Amplitude B (rad)").grid(row=10, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(sim_frame, textvariable=self.amp_b_var).grid(row=11, column=0, sticky=tk.EW)

        ttk.Label(sim_frame, text="Frequency (Hz)").grid(row=12, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(sim_frame, textvariable=self.frequency_var).grid(row=13, column=0, sticky=tk.EW)

        joint_frame = ttk.Frame(sim_frame)
        joint_frame.grid(row=14, column=0, sticky=tk.EW, pady=(8, 0))
        ttk.Label(joint_frame, text="Joint A").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(joint_frame, width=6, textvariable=self.joint_a_var).grid(row=0, column=1, padx=(6, 12))
        ttk.Label(joint_frame, text="Joint B").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(joint_frame, width=6, textvariable=self.joint_b_var).grid(row=0, column=3, padx=(6, 12))
        ttk.Label(joint_frame, text="Right Mode").grid(row=0, column=4, sticky=tk.W)
        right_mode_box = ttk.Combobox(
            joint_frame,
            textvariable=self.right_mode_var,
            values=RIGHT_MODE_OPTIONS,
            state="readonly",
            width=10,
        )
        right_mode_box.grid(row=0, column=5, padx=(6, 0))
        ttk.Label(joint_frame, text="Arm Mode").grid(row=0, column=6, sticky=tk.W, padx=(12, 0))
        arm_mode_box = ttk.Combobox(
            joint_frame,
            textvariable=self.arm_mode_var,
            values=ARM_MODE_OPTIONS,
            state="readonly",
            width=8,
        )
        arm_mode_box.grid(row=0, column=7, padx=(6, 0))
        joint_frame.columnconfigure(8, weight=1)

        ttk.Label(sim_frame, text="Right Phase Offset (rad)").grid(row=15, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(sim_frame, textvariable=self.phase_offset_var).grid(row=16, column=0, sticky=tk.EW)

        ttk.Label(
            sim_frame,
            text="Geometry uses joint A/B as X/Y in joint space; Arm Mode selects left/right/both control.",
            wraplength=430,
        ).grid(row=17, column=0, sticky=tk.W, pady=(6, 0))

        run_sim_btn = ttk.Button(sim_frame, text="Run Simulation", command=self._run_simulation)
        run_sim_btn.grid(row=18, column=0, sticky=tk.W, pady=(10, 0))
        self._command_buttons.append(run_sim_btn)
        sim_frame.columnconfigure(0, weight=1)

        action_frame = ttk.LabelFrame(parent, text="Quick Actions", padding=10)
        action_frame.pack(fill=tk.X, pady=(0, 8))

        test_btn = ttk.Button(action_frame, text="Run Unit Tests", command=self._run_tests)
        test_btn.pack(anchor=tk.W)
        git_btn = ttk.Button(action_frame, text="Show Git Status", command=self._git_status)
        git_btn.pack(anchor=tk.W, pady=(8, 0))
        open_repo_btn = ttk.Button(action_frame, text="Open Project Folder", command=self._open_repo_folder)
        open_repo_btn.pack(anchor=tk.W, pady=(8, 0))
        feature_hub_btn = ttk.Button(action_frame, text="Open Feature Hub", command=self._open_feature_hub)
        feature_hub_btn.pack(anchor=tk.W, pady=(8, 0))
        stop_btn = ttk.Button(action_frame, text="Stop Current Command", command=self._stop_current_command)
        stop_btn.pack(anchor=tk.W, pady=(8, 0))

        self._command_buttons.extend([test_btn, git_btn, open_repo_btn, feature_hub_btn])
        self._stop_button = stop_btn
        self._stop_button.state(["disabled"])

        resources_frame = ttk.LabelFrame(parent, text="Open Key Files", padding=10)
        resources_frame.pack(fill=tk.BOTH, expand=True)

        self.resource_list = tk.Listbox(
            resources_frame,
            height=12,
            selectmode=tk.BROWSE,
            exportselection=False,
        )
        for path in self._resource_paths:
            self.resource_list.insert(tk.END, path)
        self.resource_list.pack(fill=tk.BOTH, expand=True)
        self.resource_list.selection_set(0)
        self.resource_list.bind("<<ListboxSelect>>", self._on_resource_selected)
        self.resource_list.bind("<Double-Button-1>", self._open_selected_resource_event)
        self.resource_list.bind("<Return>", self._open_selected_resource_event)
        self.resource_list.bind("<Control-Button-1>", self._open_resource_ctrl_click)

        open_file_btn = ttk.Button(resources_frame, text="Open Selected File", command=self._open_selected_resource)
        open_file_btn.pack(anchor=tk.W, pady=(8, 0))
        self._command_buttons.append(open_file_btn)
        ttk.Label(resources_frame, text="Tip: double-click, Enter, or Ctrl+click a file to open it.").pack(
            anchor=tk.W, pady=(4, 0)
        )

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(status_frame, text="Status:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(6, 0))

        log_frame = ttk.LabelFrame(parent, text="Command Output", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.configure(state=tk.DISABLED)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        log_buttons = ttk.Frame(parent)
        log_buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(log_buttons, text="Clear Output", command=self._clear_output).pack(side=tk.LEFT)
        ttk.Button(log_buttons, text="Copy Output", command=self._copy_output).pack(side=tk.LEFT, padx=(8, 0))

    def _refresh_environment(self) -> None:
        self.python_var.set(resolve_python_executable(self.root_dir))
        venv_exists = (self.root_dir / ".venv" / "Scripts" / "python.exe").exists()
        suffix = "(.venv detected)" if venv_exists else "(using current interpreter)"
        self.status_var.set(f"Idle {suffix}")

    def _create_venv(self) -> None:
        if (self.root_dir / ".venv" / "Scripts" / "python.exe").exists():
            messagebox.showinfo("Virtual Environment", ".venv already exists.")
            self._refresh_environment()
            return
        self._run_command(
            [self.python_var.get(), "-m", "venv", ".venv"],
            description="Create virtual environment",
        )

    def _install_requirements(self) -> None:
        self._run_command(
            [self.python_var.get(), "-m", "pip", "install", "-r", "requirements.txt"],
            description="Install requirements",
        )

    def _run_tests(self) -> None:
        self._run_command(
            [self.python_var.get(), "-m", "unittest", "discover", "-s", "tests"],
            description="Run unit tests",
        )

    def _git_status(self) -> None:
        self._run_command(["git", "status", "--short", "--branch"], description="Git status")

    def _browse_model(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select MuJoCo XML model",
            initialdir=str(self.root_dir),
            filetypes=[("MuJoCo XML", "*.xml"), ("XML", "*.xml"), ("All files", "*.*")],
        )
        if not selected:
            return

        selected_path = Path(selected)
        try:
            relative = selected_path.relative_to(self.root_dir)
            self.model_var.set(str(relative).replace("\\", "/"))
        except ValueError:
            self.model_var.set(str(selected_path))

    def get_current_simulation_settings(self) -> dict:
        return {
            "model": self.model_var.get().strip(),
            "sim_seconds": float(self.sim_seconds_var.get()),
            "joint_offset": float(self.joint_offset_var.get()),
            "trajectory": self.trajectory_var.get().strip(),
            "amp_a": float(self.amp_a_var.get()),
            "amp_b": float(self.amp_b_var.get()),
            "frequency": float(self.frequency_var.get()),
            "joint_a": int(self.joint_a_var.get()),
            "joint_b": int(self.joint_b_var.get()),
            "right_mode": self.right_mode_var.get().strip(),
            "arm_mode": self.arm_mode_var.get().strip(),
            "phase_offset": float(self.phase_offset_var.get()),
        }

    def get_simulation_settings_from_inputs(self) -> dict:
        settings = self.get_current_simulation_settings()
        self._validate_simulation_settings(settings)
        return settings

    def apply_simulation_settings(self, settings: dict) -> None:
        if "model" in settings:
            self.model_var.set(str(settings["model"]))
        if "sim_seconds" in settings:
            self.sim_seconds_var.set(str(settings["sim_seconds"]))
        if "joint_offset" in settings:
            self.joint_offset_var.set(str(settings["joint_offset"]))
        if "trajectory" in settings:
            self.trajectory_var.set(str(settings["trajectory"]))
        if "amp_a" in settings:
            self.amp_a_var.set(str(settings["amp_a"]))
        if "amp_b" in settings:
            self.amp_b_var.set(str(settings["amp_b"]))
        if "frequency" in settings:
            self.frequency_var.set(str(settings["frequency"]))
        if "joint_a" in settings:
            self.joint_a_var.set(str(settings["joint_a"]))
        if "joint_b" in settings:
            self.joint_b_var.set(str(settings["joint_b"]))
        if "right_mode" in settings:
            self.right_mode_var.set(str(settings["right_mode"]))
        if "arm_mode" in settings:
            self.arm_mode_var.set(str(settings["arm_mode"]))
        if "phase_offset" in settings:
            self.phase_offset_var.set(str(settings["phase_offset"]))

    def _validate_simulation_settings(self, settings: dict) -> None:
        if settings["sim_seconds"] <= 0:
            raise ValueError("Simulation seconds must be > 0.")
        if settings["trajectory"] not in TRAJECTORY_OPTIONS:
            raise ValueError(f"Unsupported trajectory: {settings['trajectory']}")
        if settings["right_mode"] not in RIGHT_MODE_OPTIONS:
            raise ValueError(f"Unsupported right mode: {settings['right_mode']}")
        if settings["arm_mode"] not in ARM_MODE_OPTIONS:
            raise ValueError(f"Unsupported arm mode: {settings['arm_mode']}")
        if settings["frequency"] < 0:
            raise ValueError("Frequency must be >= 0.")
        if settings["amp_a"] < 0 or settings["amp_b"] < 0:
            raise ValueError("Amplitude values must be >= 0.")
        if not 0 <= settings["joint_a"] <= 6 or not 0 <= settings["joint_b"] <= 6:
            raise ValueError("Joint A and Joint B must be integers in [0, 6].")

        max_seconds = float(self.safety_max_seconds_var.get())
        max_amp = float(self.safety_max_amplitude_var.get())
        max_freq = float(self.safety_max_frequency_var.get())
        if settings["sim_seconds"] > max_seconds:
            raise ValueError(f"Simulation seconds exceeds safety limit ({max_seconds}).")
        if max(settings["amp_a"], settings["amp_b"]) > max_amp:
            raise ValueError(f"Amplitude exceeds safety limit ({max_amp}).")
        if settings["frequency"] > max_freq:
            raise ValueError(f"Frequency exceeds safety limit ({max_freq}).")

    def run_external_command(self, command: list[str], description: str, source: str, settings: dict) -> None:
        self._run_command(
            command,
            description=description,
            metadata={"record_run": False, "source": source, "settings": settings},
        )

    def run_simulation_with_settings(self, settings: dict, source: str, description: str) -> None:
        self._validate_simulation_settings(settings)
        command = build_simulation_command(
            python_executable=self.python_var.get(),
            model=settings["model"],
            sim_seconds=settings["sim_seconds"],
            joint_offset=settings["joint_offset"],
            trajectory=settings["trajectory"],
            amp_a=settings["amp_a"],
            amp_b=settings["amp_b"],
            frequency=settings["frequency"],
            joint_a=settings["joint_a"],
            joint_b=settings["joint_b"],
            right_mode=settings["right_mode"],
            arm_mode=settings["arm_mode"],
            phase_offset=settings["phase_offset"],
        )
        self._run_command(
            command,
            description=description,
            metadata={
                "record_run": bool(self.record_runs_var.get()),
                "source": source,
                "settings": dict(settings),
            },
        )

    def start_batch_sweep(self, jobs: list[dict]) -> None:
        if not jobs:
            return
        if self._active_process is not None or self._sweep_queue:
            messagebox.showwarning("Batch Sweep", "A command is already running.")
            return
        self._sweep_queue = list(jobs)
        self.add_timeline_event(f"Started batch sweep with {len(jobs)} jobs.")
        self._start_next_sweep_job()

    def _start_next_sweep_job(self) -> None:
        if not self._sweep_queue:
            self.add_timeline_event("Batch sweep completed.")
            self.status_var.set("Batch sweep completed.")
            return
        settings = self._sweep_queue.pop(0)
        try:
            self.run_simulation_with_settings(
                settings=settings,
                source="batch_sweep",
                description=f"Sweep {settings['trajectory']} amp={settings['amp_a']} freq={settings['frequency']}",
            )
        except Exception as exc:
            self._append_output(f"[Control Center] Skipped sweep job: {exc}")
            self._start_next_sweep_job()

    def update_run_record(self, record_id, tag: str, notes: str) -> None:
        for record in self.run_records:
            if str(record.get("id")) == str(record_id):
                record["tag"] = tag
                record["notes"] = notes
                self._save_run_records()
                self.add_timeline_event(f"Updated run tag: {record_id} -> {tag}")
                return

    def generate_run_report(self, record: dict) -> Path:
        self.run_reports_dir.mkdir(parents=True, exist_ok=True)
        run_id = str(record.get("id", "unknown"))
        report_path = self.run_reports_dir / f"{run_id}.md"
        settings = record.get("settings", {})
        lines = [
            f"# Run Report: {run_id}",
            "",
            f"- timestamp: {record.get('timestamp')}",
            f"- description: {record.get('description')}",
            f"- source: {record.get('source')}",
            f"- return_code: {record.get('return_code')}",
            f"- tag: {record.get('tag', 'unlabeled')}",
            f"- notes: {record.get('notes', '')}",
            "",
            "## Settings",
            "",
        ]
        for key in sorted(settings.keys()):
            lines.append(f"- {key}: {settings[key]}")
        lines.append("")
        lines.append("## Command")
        lines.append("")
        lines.append(f"`{record.get('command', '')}`")
        lines.append("")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        record["report_path"] = str(report_path.relative_to(self.root_dir)).replace("\\", "/")
        self._save_run_records()
        self.add_timeline_event(f"Generated run report: {run_id}")
        return report_path

    def _run_simulation(self) -> None:
        try:
            settings = self.get_simulation_settings_from_inputs()
        except ValueError as exc:
            messagebox.showerror("Invalid Simulation Input", str(exc))
            return
        self.run_simulation_with_settings(settings=settings, source="manual", description="Run simulation")

    def _open_repo_folder(self) -> None:
        self._open_path(self.root_dir)

    def _open_feature_hub(self) -> None:
        if self._feature_hub_window is not None and self._feature_hub_window.winfo_exists():
            self._feature_hub_window.lift()
            self._feature_hub_window.focus_force()
            return
        self._feature_hub_window = FeatureHubWindow(self)
        self.add_timeline_event("Opened Feature Hub.")

    def _on_resource_selected(self, _event: tk.Event | None = None) -> None:
        if not self.resource_list.curselection():
            return
        selection_index = self.resource_list.curselection()[0]
        relative_path = self.resource_list.get(selection_index)
        self.status_var.set(f"Selected: {relative_path} (double-click, Enter, or Ctrl+click to open)")

    def _open_selected_resource_event(self, _event: tk.Event | None = None) -> None:
        self._open_selected_resource()

    def _open_resource_ctrl_click(self, event: tk.Event) -> str:
        index = self.resource_list.nearest(event.y)
        self.resource_list.selection_clear(0, tk.END)
        self.resource_list.selection_set(index)
        self.resource_list.activate(index)
        self._open_selected_resource()
        return "break"

    def _open_selected_resource(self) -> None:
        if not self.resource_list.curselection():
            messagebox.showinfo("Open File", "Select a file from the list first.")
            return
        selection_index = self.resource_list.curselection()[0]
        relative_path = self.resource_list.get(selection_index)
        self._open_path(self.root_dir / relative_path)

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showerror("Path Missing", f"Path does not exist:\n{path}")
            return
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            self._append_output(f"[Control Center] Opened: {path}")
            self.status_var.set(f"Opened: {path.name}")
        except Exception as exc:
            messagebox.showerror("Open Failed", f"Could not open path:\n{path}\n\n{exc}")

    def _stop_current_command(self) -> None:
        process = self._active_process
        if process is None:
            return
        process.terminate()
        self._sweep_queue.clear()
        self._append_output("[Control Center] Sent terminate signal to active process.")
        self.add_timeline_event("Stopped active command.")

    def _clear_output(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _copy_output(self) -> None:
        text = self.log_text.get("1.0", tk.END).strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Copied output to clipboard.")

    def _set_command_state(self, running: bool) -> None:
        if running:
            for button in self._command_buttons:
                button.state(["disabled"])
            self._stop_button.state(["!disabled"])
            return

        for button in self._command_buttons:
            button.state(["!disabled"])
        self._stop_button.state(["disabled"])
        self._refresh_environment()

    def _run_command(self, command: list[str], description: str, metadata: dict | None = None) -> None:
        with self._command_lock:
            if self._active_process is not None:
                messagebox.showwarning("Command Running", "Wait for the active command to finish first.")
                return
            self._set_command_state(running=True)
            self.status_var.set(f"Running: {description}")
            command_display = subprocess.list2cmdline(command)
            self._append_output(f"\n$ {command_display}\n")
            self._pending_command_metadata = dict(metadata or {})
            self.add_timeline_event(f"Started command: {description}")

        worker = threading.Thread(
            target=self._command_worker,
            args=(command, description, dict(metadata or {})),
            daemon=True,
        )
        worker.start()

    def _command_worker(self, command: list[str], description: str, metadata: dict) -> None:
        try:
            process = subprocess.Popen(
                command,
                cwd=str(self.root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            self.log_queue.put(("log", f"[Control Center] Failed to start command: {exc}"))
            self.log_queue.put(
                (
                    "done",
                    {
                        "description": description,
                        "return_code": 1,
                        "command": command,
                        "metadata": metadata,
                    },
                )
            )
            return

        self._active_process = process
        assert process.stdout is not None
        for line in process.stdout:
            self.log_queue.put(("log", line.rstrip()))

        return_code = process.wait()
        self.log_queue.put(("log", f"[Control Center] {description} finished with exit code {return_code}."))
        self.log_queue.put(
            (
                "done",
                {
                    "description": description,
                    "return_code": return_code,
                    "command": command,
                    "metadata": metadata,
                },
            )
        )

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._append_output(payload)
            elif kind == "done":
                self._active_process = None
                if isinstance(payload, dict):
                    description = str(payload.get("description", "command"))
                    self.status_var.set(f"Idle (completed: {description})")
                    self._on_command_finished(payload)
                else:
                    self.status_var.set(f"Idle (completed: {payload})")
                self._set_command_state(running=False)

        self.after(120, self._drain_queue)

    def _on_command_finished(self, payload: dict) -> None:
        description = str(payload.get("description", "command"))
        return_code = int(payload.get("return_code", 1))
        command = payload.get("command", [])
        metadata = payload.get("metadata", {}) or {}
        self.add_timeline_event(f"Completed command: {description} (rc={return_code})")

        if metadata.get("record_run"):
            run_id = f"run-{self._next_run_id:04d}"
            self._next_run_id += 1
            record = {
                "id": run_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "description": description,
                "source": metadata.get("source", "manual"),
                "return_code": return_code,
                "command": subprocess.list2cmdline(command) if isinstance(command, list) else str(command),
                "settings": metadata.get("settings", {}),
                "tag": "success" if return_code == 0 else "other",
                "notes": "",
            }
            self.run_records.append(record)
            self._save_run_records()
            self.add_timeline_event(f"Recorded run: {run_id}")
            if self.auto_report_var.get():
                self.generate_run_report(record)

        if self._sweep_queue:
            self._start_next_sweep_job()

    def _append_output(self, text: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{text}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)


def launch() -> None:
    app = CapstoneControlCenter()
    app.mainloop()
