"""Advanced feature hub for Control Center."""

from __future__ import annotations

import shlex
import subprocess
import tkinter as tk
from itertools import product
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .utils import TASK_TEMPLATES, load_json_object, parse_number_list, save_json_object, trajectory_point, trajectory_samples


class FeatureHubWindow(tk.Toplevel):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app
        self.title("Feature Hub")
        self.geometry("1120x720")
        self.minsize(980, 640)

        self.preset_name_var = tk.StringVar(value="my_preset")
        self.template_var = tk.StringVar(value=list(TASK_TEMPLATES.keys())[0])
        self.amp_list_var = tk.StringVar(value="0.10,0.20,0.30")
        self.freq_list_var = tk.StringVar(value="0.10,0.20")
        self.sweep_seconds_var = tk.StringVar(value="20")
        self.failure_tag_var = tk.StringVar(value="success")
        self.dataset_root_var = tk.StringVar(value=str(self.app.root_dir / "data"))
        self.training_script_var = tk.StringVar(value="")
        self.training_args_var = tk.StringVar(value="")
        self.inference_script_var = tk.StringVar(value="")
        self.inference_args_var = tk.StringVar(value="")
        self.exp_config_var = tk.StringVar(value="")

        self.scope_running = False
        self.scope_t = 0.0
        self.scope_x: list[float] = []
        self.scope_y: list[float] = []

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.tab_traj = ttk.Frame(notebook, padding=8)
        self.tab_runs = ttk.Frame(notebook, padding=8)
        self.tab_data = ttk.Frame(notebook, padding=8)
        self.tab_collab = ttk.Frame(notebook, padding=8)
        notebook.add(self.tab_traj, text="Trajectory Lab")
        notebook.add(self.tab_runs, text="Runs/Experiments")
        notebook.add(self.tab_data, text="Data/ML Ops")
        notebook.add(self.tab_collab, text="PR/Collab")

        self._build_trajectory_tab()
        self._build_runs_tab()
        self._build_data_tab()
        self._build_collab_tab()
        self.refresh_all()

    def _build_trajectory_tab(self) -> None:
        preset = ttk.LabelFrame(self.tab_traj, text="1) Presets + 17) Task Templates", padding=8)
        preset.pack(fill=tk.X, pady=(0, 8))
        ttk.Entry(preset, textvariable=self.preset_name_var).grid(row=0, column=0, sticky=tk.EW)
        ttk.Button(preset, text="Save Preset", command=self.save_preset).grid(row=0, column=1, padx=4)
        self.preset_list = tk.Listbox(preset, height=5, exportselection=False)
        self.preset_list.grid(row=1, column=0, sticky=tk.NSEW, pady=4)
        ttk.Button(preset, text="Load", command=self.load_preset).grid(row=1, column=1, sticky=tk.NW, padx=4)
        ttk.Button(preset, text="Delete", command=self.delete_preset).grid(row=1, column=1, sticky=tk.SW, padx=4, pady=(30, 0))
        ttk.Combobox(preset, textvariable=self.template_var, values=list(TASK_TEMPLATES.keys()), state="readonly").grid(
            row=2, column=0, sticky=tk.EW, pady=(6, 0)
        )
        ttk.Button(preset, text="Apply Template", command=self.apply_template).grid(row=2, column=1, padx=4, pady=(6, 0))
        preset.columnconfigure(0, weight=1)
        preset.rowconfigure(1, weight=1)

        safety = ttk.LabelFrame(self.tab_traj, text="9) Safety Limits", padding=8)
        safety.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(safety, text="Max Sec").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(safety, textvariable=self.app.safety_max_seconds_var, width=10).grid(row=0, column=1, padx=(6, 16))
        ttk.Label(safety, text="Max Amp").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(safety, textvariable=self.app.safety_max_amplitude_var, width=10).grid(row=0, column=3, padx=(6, 16))
        ttk.Label(safety, text="Max Freq").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(safety, textvariable=self.app.safety_max_frequency_var, width=10).grid(row=0, column=5, padx=(6, 16))
        ttk.Button(safety, text="Apply", command=lambda: self.app.add_timeline_event("Updated safety limits")).grid(row=0, column=6)

        canvas_frame = ttk.LabelFrame(self.tab_traj, text="2) Plot Preview + 3) Live Scope", padding=8)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas = tk.Canvas(canvas_frame, height=220, background="#12161d")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.scope_canvas = tk.Canvas(canvas_frame, height=180, background="#121a22")
        self.scope_canvas.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        row = ttk.Frame(canvas_frame)
        row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(row, text="Refresh Preview", command=self.refresh_preview).pack(side=tk.LEFT)
        ttk.Button(row, text="Start Scope", command=self.start_scope).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Stop Scope", command=self.stop_scope).pack(side=tk.LEFT)

    def _build_runs_tab(self) -> None:
        top = ttk.Frame(self.tab_runs)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Checkbutton(top, text="4) Record Runs", variable=self.app.record_runs_var).pack(side=tk.LEFT)
        ttk.Checkbutton(top, text="8) Auto Reports", variable=self.app.auto_report_var).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(top, text="Refresh", command=self.refresh_runs).pack(side=tk.RIGHT)

        self.run_list = tk.Listbox(self.tab_runs, height=8, exportselection=False)
        self.run_list.pack(fill=tk.X)
        btns = ttk.Frame(self.tab_runs)
        btns.pack(fill=tk.X, pady=(6, 8))
        ttk.Button(btns, text="Replay Selected", command=self.replay_selected).pack(side=tk.LEFT)
        ttk.Button(btns, text="Generate Report", command=self.report_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Refresh Timeline", command=self.refresh_timeline).pack(side=tk.LEFT)

        compare = ttk.LabelFrame(self.tab_runs, text="6) Compare Runs", padding=8)
        compare.pack(fill=tk.X, pady=(0, 8))
        self.compare_a = tk.StringVar(value="")
        self.compare_b = tk.StringVar(value="")
        self.compare_box_a = ttk.Combobox(compare, textvariable=self.compare_a, values=[], state="readonly")
        self.compare_box_b = ttk.Combobox(compare, textvariable=self.compare_b, values=[], state="readonly")
        self.compare_box_a.grid(row=0, column=0, sticky=tk.EW)
        self.compare_box_b.grid(row=0, column=1, sticky=tk.EW, padx=6)
        ttk.Button(compare, text="Compare", command=self.compare_runs).grid(row=0, column=2)
        self.compare_text = tk.Text(compare, height=6, wrap=tk.WORD)
        self.compare_text.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW, pady=(6, 0))
        compare.columnconfigure(0, weight=1)
        compare.columnconfigure(1, weight=1)

        tag = ttk.LabelFrame(self.tab_runs, text="7) Failure Tagging", padding=8)
        tag.pack(fill=tk.X, pady=(0, 8))
        ttk.Combobox(tag, textvariable=self.failure_tag_var, values=("success", "grasp_fail", "placement_fail", "collision", "timeout", "other"), state="readonly").grid(row=0, column=0, sticky=tk.W)
        self.failure_notes = ttk.Entry(tag)
        self.failure_notes.grid(row=0, column=1, sticky=tk.EW, padx=6)
        ttk.Button(tag, text="Apply to Selected", command=self.apply_tag).grid(row=0, column=2)
        tag.columnconfigure(1, weight=1)

        launch = ttk.LabelFrame(self.tab_runs, text="5) Experiment Launcher + 10) Batch Sweep", padding=8)
        launch.pack(fill=tk.X, pady=(0, 8))
        self.exp_box = ttk.Combobox(launch, textvariable=self.exp_config_var, values=[], state="readonly")
        self.exp_box.grid(row=0, column=0, sticky=tk.EW)
        ttk.Button(launch, text="Load Config", command=self.load_experiment_config).grid(row=0, column=1, padx=6)
        ttk.Button(launch, text="Launch", command=self.launch_experiment).grid(row=0, column=2)
        ttk.Entry(launch, textvariable=self.amp_list_var).grid(row=1, column=0, sticky=tk.EW, pady=(6, 0))
        ttk.Entry(launch, textvariable=self.freq_list_var).grid(row=1, column=1, sticky=tk.EW, pady=(6, 0), padx=6)
        ttk.Entry(launch, textvariable=self.sweep_seconds_var, width=10).grid(row=1, column=2, pady=(6, 0))
        ttk.Button(launch, text="Start Sweep", command=self.start_sweep).grid(row=1, column=3, padx=6, pady=(6, 0))
        launch.columnconfigure(0, weight=1)
        launch.columnconfigure(1, weight=1)

        timeline_box = ttk.LabelFrame(self.tab_runs, text="18) Session Timeline", padding=8)
        timeline_box.pack(fill=tk.BOTH, expand=True)
        self.timeline_list = tk.Listbox(timeline_box, exportselection=False)
        self.timeline_list.pack(fill=tk.BOTH, expand=True)

    def _build_data_tab(self) -> None:
        doctor = ttk.LabelFrame(self.tab_data, text="11) Environment Doctor", padding=8)
        doctor.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        ttk.Button(doctor, text="Run Doctor", command=self.run_doctor).pack(anchor=tk.W)
        self.doctor_text = tk.Text(doctor, height=8, wrap=tk.WORD)
        self.doctor_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        dataset = ttk.LabelFrame(self.tab_data, text="12) Dataset Browser + 13) Validator", padding=8)
        dataset.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        row = ttk.Frame(dataset)
        row.pack(fill=tk.X)
        ttk.Entry(row, textvariable=self.dataset_root_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Browse", command=self.browse_dataset_root).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Scan", command=self.scan_datasets).pack(side=tk.LEFT)
        self.dataset_list = tk.Listbox(dataset, height=6, exportselection=False)
        self.dataset_list.pack(fill=tk.X, pady=(6, 0))
        row2 = ttk.Frame(dataset)
        row2.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(row2, text="Open Folder", command=self.open_dataset).pack(side=tk.LEFT)
        ttk.Button(row2, text="Validate Selected", command=self.validate_dataset).pack(side=tk.LEFT, padx=6)
        self.dataset_validation = tk.Text(dataset, height=6, wrap=tk.WORD)
        self.dataset_validation.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        jobs = ttk.LabelFrame(self.tab_data, text="14) Training Starter + 15) Inference Demo", padding=8)
        jobs.pack(fill=tk.X)
        ttk.Entry(jobs, textvariable=self.training_script_var).grid(row=0, column=0, sticky=tk.EW)
        ttk.Entry(jobs, textvariable=self.training_args_var).grid(row=0, column=1, sticky=tk.EW, padx=6)
        ttk.Button(jobs, text="Start Training", command=self.start_training).grid(row=0, column=2)
        ttk.Entry(jobs, textvariable=self.inference_script_var).grid(row=1, column=0, sticky=tk.EW, pady=(6, 0))
        ttk.Entry(jobs, textvariable=self.inference_args_var).grid(row=1, column=1, sticky=tk.EW, padx=6, pady=(6, 0))
        ttk.Button(jobs, text="Run Inference", command=self.start_inference).grid(row=1, column=2, pady=(6, 0))
        jobs.columnconfigure(0, weight=1)
        jobs.columnconfigure(1, weight=1)

    def _build_collab_tab(self) -> None:
        box = ttk.LabelFrame(self.tab_collab, text="16) PR Helper", padding=8)
        box.pack(fill=tk.BOTH, expand=True)
        row = ttk.Frame(box)
        row.pack(fill=tk.X)
        ttk.Button(row, text="Generate Draft", command=self.generate_pr_draft).pack(side=tk.LEFT)
        ttk.Button(row, text="Copy Draft", command=self.copy_pr_draft).pack(side=tk.LEFT, padx=6)
        self.pr_text = tk.Text(box, wrap=tk.WORD)
        self.pr_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def refresh_all(self) -> None:
        self.refresh_presets()
        self.refresh_runs()
        self.refresh_timeline()
        self.scan_datasets()
        self.refresh_experiment_configs()
        self.refresh_preview()

    def _preset_path(self) -> Path:
        return self.app.root_dir / "configs" / "trajectory_presets.json"

    def _load_presets(self) -> dict:
        return load_json_object(self._preset_path(), default={"presets": {}}).get("presets", {})

    def refresh_presets(self) -> None:
        self.preset_list.delete(0, tk.END)
        for key in sorted(self._load_presets().keys()):
            self.preset_list.insert(tk.END, key)

    def save_preset(self) -> None:
        name = self.preset_name_var.get().strip()
        if not name:
            return
        presets = self._load_presets()
        presets[name] = self.app.get_current_simulation_settings()
        save_json_object(self._preset_path(), {"presets": presets})
        self.refresh_presets()
        self.app.add_timeline_event(f"Saved preset {name}")

    def load_preset(self) -> None:
        if not self.preset_list.curselection():
            return
        name = self.preset_list.get(self.preset_list.curselection()[0])
        payload = self._load_presets().get(name, {})
        self.app.apply_simulation_settings(payload)
        self.refresh_preview()

    def delete_preset(self) -> None:
        if not self.preset_list.curselection():
            return
        name = self.preset_list.get(self.preset_list.curselection()[0])
        presets = self._load_presets()
        presets.pop(name, None)
        save_json_object(self._preset_path(), {"presets": presets})
        self.refresh_presets()

    def apply_template(self) -> None:
        payload = TASK_TEMPLATES.get(self.template_var.get(), {})
        self.app.apply_simulation_settings(payload)
        self.refresh_preview()

    def refresh_preview(self) -> None:
        s = self.app.get_current_simulation_settings()
        _, xs, ys = trajectory_samples(
            trajectory=s["trajectory"], amp_a=s["amp_a"], amp_b=s["amp_b"], frequency=s["frequency"], duration_sec=max(s["sim_seconds"], 8.0), points=240
        )
        self.preview_canvas.delete("all")
        w = int(self.preview_canvas.winfo_width() or 600)
        h = int(self.preview_canvas.winfo_height() or 220)
        self.preview_canvas.create_rectangle(1, 1, w - 1, h - 1, outline="#364255")
        min_x, max_x = min(xs or [0]), max(xs or [1])
        min_y, max_y = min(ys or [0]), max(ys or [1])
        sx = max(max_x - min_x, 1e-6)
        sy = max(max_y - min_y, 1e-6)
        pts = []
        for x, y in zip(xs, ys):
            px = 20 + ((x - min_x) / sx) * (w - 40)
            py = h - 20 - ((y - min_y) / sy) * (h - 40)
            pts += [px, py]
        if len(pts) > 3:
            self.preview_canvas.create_line(*pts, fill="#64ddff", width=2, smooth=True)

    def start_scope(self) -> None:
        self.scope_running = True
        self.scope_t = 0.0
        self.scope_x.clear()
        self.scope_y.clear()
        self._tick_scope()

    def stop_scope(self) -> None:
        self.scope_running = False

    def _tick_scope(self) -> None:
        if not self.scope_running:
            return
        s = self.app.get_current_simulation_settings()
        x, y = trajectory_point(trajectory=s["trajectory"], t_sec=self.scope_t, frequency=s["frequency"], amp_a=s["amp_a"], amp_b=s["amp_b"])
        self.scope_x.append(x + s["joint_offset"])
        self.scope_y.append(y)
        self.scope_x = self.scope_x[-260:]
        self.scope_y = self.scope_y[-260:]
        self.scope_canvas.delete("all")
        w = int(self.scope_canvas.winfo_width() or 600)
        h = int(self.scope_canvas.winfo_height() or 180)
        self.scope_canvas.create_rectangle(1, 1, w - 1, h - 1, outline="#364255")
        if len(self.scope_x) > 1:
            all_vals = self.scope_x + self.scope_y
            mn, mx = min(all_vals), max(all_vals)
            span = max(mx - mn, 1e-6)
            px = []
            py = []
            for idx, (vx, vy) in enumerate(zip(self.scope_x, self.scope_y)):
                x_pos = 12 + (idx / max(len(self.scope_x) - 1, 1)) * (w - 24)
                px += [x_pos, h - 12 - ((vx - mn) / span) * (h - 24)]
                py += [x_pos, h - 12 - ((vy - mn) / span) * (h - 24)]
            self.scope_canvas.create_line(*px, fill="#00e5ff", width=2)
            self.scope_canvas.create_line(*py, fill="#ffb74d", width=2)
        self.scope_t += 0.05
        self.after(70, self._tick_scope)

    def refresh_runs(self) -> None:
        self.run_list.delete(0, tk.END)
        labels: list[str] = []
        for record in self.app.run_records:
            label = f"{record.get('id')} | rc={record.get('return_code')} | {record.get('description')}"
            labels.append(label)
            self.run_list.insert(tk.END, label)
        self.compare_box_a["values"] = labels
        self.compare_box_b["values"] = labels
        if labels and not self.compare_a.get():
            self.compare_a.set(labels[0])
        if len(labels) > 1 and not self.compare_b.get():
            self.compare_b.set(labels[1])

    def _selected_record(self) -> dict | None:
        if not self.run_list.curselection():
            return None
        idx = self.run_list.curselection()[0]
        if idx < 0 or idx >= len(self.app.run_records):
            return None
        return self.app.run_records[idx]

    def replay_selected(self) -> None:
        record = self._selected_record()
        if not record:
            return
        settings = record.get("settings")
        if not isinstance(settings, dict):
            return
        self.app.apply_simulation_settings(settings)
        self.app.run_simulation_with_settings(settings=settings, source="replay", description=f"Replay {record.get('id')}")

    def report_selected(self) -> None:
        record = self._selected_record()
        if not record:
            return
        self.app.generate_run_report(record)

    def compare_runs(self) -> None:
        def _find(label: str) -> dict | None:
            run_id = label.split("|")[0].strip()
            for rec in self.app.run_records:
                if str(rec.get("id")) == run_id:
                    return rec
            return None

        a = _find(self.compare_a.get())
        b = _find(self.compare_b.get())
        self.compare_text.delete("1.0", tk.END)
        if not a or not b:
            return
        lines = [f"A={a.get('id')}  rc={a.get('return_code')}", f"B={b.get('id')}  rc={b.get('return_code')}", ""]
        sa = a.get("settings", {})
        sb = b.get("settings", {})
        for key in sorted(set(sa.keys()) | set(sb.keys())):
            left = sa.get(key, "-")
            right = sb.get(key, "-")
            lines.append(f"{key}: {left} {'!=' if left != right else '=='} {right}")
        self.compare_text.insert(tk.END, "\n".join(lines))

    def apply_tag(self) -> None:
        record = self._selected_record()
        if not record:
            return
        self.app.update_run_record(
            record_id=record.get("id"),
            tag=self.failure_tag_var.get().strip(),
            notes=self.failure_notes.get().strip(),
        )
        self.refresh_runs()

    def refresh_experiment_configs(self) -> None:
        configs = sorted(str(path.relative_to(self.app.root_dir)).replace("\\", "/") for path in (self.app.root_dir / "configs").glob("*.json"))
        self.exp_box["values"] = configs
        if configs and not self.exp_config_var.get():
            self.exp_config_var.set(configs[0])

    def load_experiment_config(self) -> None:
        value = self.exp_config_var.get().strip()
        if not value:
            return
        path = self.app.root_dir / value
        if not path.exists():
            messagebox.showerror("Config", f"Missing config: {path}")
            return
        payload = load_json_object(path, default={})
        sim_payload = payload.get("simulation", payload)
        if isinstance(sim_payload, dict):
            self.app.apply_simulation_settings(sim_payload)
            self.refresh_preview()

    def launch_experiment(self) -> None:
        self.load_experiment_config()
        settings = self.app.get_current_simulation_settings()
        self.app.run_simulation_with_settings(settings=settings, source="experiment_launcher", description=f"Experiment {self.exp_config_var.get() or settings['trajectory']}")

    def start_sweep(self) -> None:
        try:
            amps = parse_number_list(self.amp_list_var.get())
            freqs = parse_number_list(self.freq_list_var.get())
            sim_seconds = float(self.sweep_seconds_var.get())
            if sim_seconds <= 0:
                raise ValueError("Sweep seconds must be > 0")
        except ValueError as exc:
            messagebox.showerror("Sweep", str(exc))
            return
        base = self.app.get_current_simulation_settings()
        jobs = []
        for amp, freq in product(amps, freqs):
            job = dict(base)
            job["amp_a"] = float(amp)
            job["frequency"] = float(freq)
            job["sim_seconds"] = float(sim_seconds)
            jobs.append(job)
        self.app.start_batch_sweep(jobs)

    def refresh_timeline(self) -> None:
        self.timeline_list.delete(0, tk.END)
        for event in self.app.session_events[-200:]:
            self.timeline_list.insert(tk.END, f"{event['timestamp']} | {event['message']}")

    def run_doctor(self) -> None:
        lines = [f"repo: {self.app.root_dir}"]
        checks = [
            self.app.root_dir / "aloha.xml",
            self.app.root_dir / "joint_position_actuators.xml",
            self.app.root_dir / "keyframe_ctrl.xml",
            self.app.root_dir / "assets",
            self.app.root_dir / ".venv" / "Scripts" / "python.exe",
        ]
        for path in checks:
            lines.append(f"[{'OK' if path.exists() else 'MISS'}] {path}")
        try:
            status = subprocess.run(["git", "status", "--short", "--branch"], cwd=str(self.app.root_dir), capture_output=True, text=True, timeout=10).stdout.strip()
            lines.append("")
            lines.append(status or "(clean)")
        except Exception as exc:
            lines.append(f"git status failed: {exc}")
        self.doctor_text.delete("1.0", tk.END)
        self.doctor_text.insert(tk.END, "\n".join(lines))

    def browse_dataset_root(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.dataset_root_var.get() or str(self.app.root_dir))
        if selected:
            self.dataset_root_var.set(selected)
            self.scan_datasets()

    def scan_datasets(self) -> None:
        root = Path(self.dataset_root_var.get()).expanduser()
        self.dataset_list.delete(0, tk.END)
        if not root.exists():
            self.dataset_list.insert(tk.END, f"[missing] {root}")
            return
        for folder in sorted([p for p in root.iterdir() if p.is_dir()]):
            count = len([p for p in folder.rglob("*") if p.is_file()])
            self.dataset_list.insert(tk.END, f"{folder.name} | {count} files")

    def _selected_dataset(self) -> Path | None:
        root = Path(self.dataset_root_var.get()).expanduser()
        if not self.dataset_list.curselection():
            return None
        label = self.dataset_list.get(self.dataset_list.curselection()[0])
        name = label.split("|")[0].strip()
        path = root / name
        return path if path.exists() else None

    def open_dataset(self) -> None:
        path = self._selected_dataset()
        if path is None:
            return
        try:
            import os

            os.startfile(str(path))  # type: ignore[attr-defined]
        except Exception:
            pass

    def validate_dataset(self) -> None:
        path = self._selected_dataset()
        self.dataset_validation.delete("1.0", tk.END)
        if path is None:
            return
        files = [p for p in path.rglob("*") if p.is_file()]
        ext_counts: dict[str, int] = {}
        for file in files:
            ext = file.suffix.lower() or "(none)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        meta_ok = any((path / name).exists() for name in ("meta.json", "metadata.json", "dataset_info.json", "info.json"))
        episode_ok = any(ext in ext_counts for ext in (".parquet", ".jsonl", ".npz", ".h5", ".hdf5"))
        lines = [f"path: {path}", f"meta file: {'OK' if meta_ok else 'WARN'}", f"episode files: {'OK' if episode_ok else 'WARN'}", ""]
        for ext, count in sorted(ext_counts.items()):
            lines.append(f"{ext}: {count}")
        self.dataset_validation.insert(tk.END, "\n".join(lines))

    def _run_script_job(self, script_raw: str, args_raw: str, description: str, source: str) -> None:
        script = Path(script_raw).expanduser()
        if not script.is_absolute():
            script = self.app.root_dir / script
        if not script.exists():
            messagebox.showerror(description, f"Missing script: {script}")
            return
        args = shlex.split(args_raw, posix=False) if args_raw.strip() else []
        command = [self.app.python_var.get(), str(script)] + args
        self.app.run_external_command(command=command, description=description, source=source, settings={})

    def start_training(self) -> None:
        self._run_script_job(self.training_script_var.get(), self.training_args_var.get(), "Training Job", "training")

    def start_inference(self) -> None:
        self._run_script_job(self.inference_script_var.get(), self.inference_args_var.get(), "Inference Demo", "inference")

    def generate_pr_draft(self) -> None:
        try:
            status = subprocess.run(["git", "status", "--short", "--branch"], cwd=str(self.app.root_dir), capture_output=True, text=True, timeout=10).stdout.strip()
            diff = subprocess.run(["git", "diff", "--stat"], cwd=str(self.app.root_dir), capture_output=True, text=True, timeout=10).stdout.strip()
            log = subprocess.run(["git", "log", "--oneline", "-n", "5"], cwd=str(self.app.root_dir), capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception as exc:
            messagebox.showerror("PR Helper", str(exc))
            return
        draft = f"""## Summary
- ...

## Why
- ...

## Changes
- ...

## How To Test
```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests
```

## Evidence
- ...

## Risks
- ...

## Follow-Ups
- ...

### Git Status
{status or "(clean)"}

### Diff Stat
{diff or "(none)"}

### Recent Commits
{log or "(none)"}
"""
        self.pr_text.delete("1.0", tk.END)
        self.pr_text.insert(tk.END, draft)

    def copy_pr_draft(self) -> None:
        text = self.pr_text.get("1.0", tk.END).strip()
        self.clipboard_clear()
        self.clipboard_append(text)

