# Capstone Project: Bimanual Manipulation Testbed

This repository is the team testbed for:

- ALOHA-style bimanual simulation in MuJoCo.
- control baselines that are easy to test and iterate on.
- research-to-implementation workflow for LeRobot + Hugging Face.
- preparing baseline learning experiments (Pi0-style or GROOT-style direction).

This README is written for beginners. If you have never used Git, Python, VS Code, or MuJoCo before, follow the steps exactly in order.

Before opening your first pull request, read `CONTRIBUTING.md` and use `.github/PULL_REQUEST_TEMPLATE.md`.

## 1. What You Are Looking At

At a high level:

1. `aloha.xml` defines the robot and world in MuJoCo XML (MJCF format).
2. `startup.py` runs a simulation entrypoint.
3. `capstone_proj/control/pid_controller.py` computes torque commands with a PD controller.
4. `tests/` verifies expected controller behavior.

You can think of this as:

- XML files = robot blueprint.
- Python controller = robot brain for the baseline.
- MuJoCo = physics engine that executes the blueprint + brain.

## 2. First-Time Setup (Windows, from zero)

### Step 1: Install Git

1. Download Git for Windows: `https://git-scm.com/download/win`
2. Run installer with default options.
3. Verify in PowerShell:
```powershell
git --version
```

Expected: a version string like `git version 2.x.x`.

### Step 2: Install Python 3.12+

Option A (beginner-friendly):

1. Download from `https://www.python.org/downloads/windows/`
2. During install, check `Add python.exe to PATH`.
3. Verify:
```powershell
python --version
pip --version
```

Option B (if you use `uv`):
```powershell
uv python install 3.12 --default
python --version
```

### Step 3: Install VS Code

1. Download: `https://code.visualstudio.com/`
2. Install and open VS Code.
3. Install extensions:
   - Python (`ms-python.python`)
   - Pylance (`ms-python.vscode-pylance`)
   - XML (`redhat.vscode-xml`)
   - GitLens (optional, helps beginners with Git history)

### Step 4: Install MuJoCo runtime dependencies

For this repo, `pip install -r requirements.txt` installs the Python MuJoCo package (`mujoco`).
No separate manual MuJoCo installation is required for standard usage here.

## 3. Clone and Open the Project

### If you are new to Git (recommended path)

```powershell
cd C:\projects
git clone https://github.com/mrypsilantis-maker/Capstone-proj.git
cd Capstone-proj
code .
```

### If you downloaded ZIP instead of Git clone

You can still run code, but you cannot contribute cleanly with branches/PRs.
Use Git clone if you plan to collaborate.

## 4. Create a Local Python Environment

From the project root (`C:\projects\Capstone-proj`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run this once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then re-open PowerShell and activate again.

## 5. Run Tests and Simulation

### Run unit tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Expected output includes:

- `Ran 3 tests`
- `OK`

### Run baseline simulation

```powershell
.\.venv\Scripts\python.exe startup.py --model aloha.xml --sim-seconds 60
```

Useful options:

```powershell
.\.venv\Scripts\python.exe startup.py --model aloha.xml --sim-seconds 120 --joint-offset 0.2
```

### Run desktop control GUI (no terminal workflow needed)

```powershell
.\.venv\Scripts\python.exe scripts/run_control_center.py
```

What this GUI provides:

- create `.venv` and install dependencies
- run tests with one click
- run simulation with editable model/time/offset inputs
- view git status
- open key docs/config/XML files directly (double-click, Enter, or Ctrl+click)
- view command logs in one place

## 6. VS Code Configuration (Recommended)

Open Command Palette: `Ctrl+Shift+P`.

1. `Python: Select Interpreter`
2. Choose `.venv` interpreter in this repo.

Optional workspace settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe",
  "python.testing.unittestEnabled": true,
  "python.testing.unittestArgs": [
    "-v",
    "-s",
    "tests",
    "-p",
    "test_*.py"
  ],
  "files.associations": {
    "*.xml": "xml"
  }
}
```

## 7. MuJoCo + XML Configuration Explained

### Core model file

- `aloha.xml` is the primary MuJoCo model.
- It references mesh files in `assets/` via `meshdir="assets"`.

### Included XML fragments

- `joint_position_actuators.xml` defines joint position actuators.
- `keyframe_ctrl.xml` defines keyframes (like a neutral pose).

If these files are missing, simulation fails during model load.

### Mesh assets

The `assets/` directory contains STL/OBJ/PNG resources used by `aloha.xml`.
If mesh files are missing or renamed, MuJoCo throws "Error opening file ..." during startup.

### Safe XML edit rules

1. Change one thing at a time.
2. Run `startup.py` after every XML change.
3. Do not rename mesh files without updating all XML references.
4. Keep units consistent (meters/radians in this model).

## 8. Repository Layout and Purpose

- `capstone_proj/control/pid_controller.py`: baseline bimanual PD controller.
- `capstone_proj/simulation/run_pid.py`: simulation CLI (`--model`, `--sim-seconds`, `--joint-offset`).
- `startup.py`: compatibility entrypoint that calls the new simulation CLI.
- `PID_Control.py`: compatibility import surface for older code.
- `capstone_proj/gui/control_center.py`: desktop control center UI for running common actions.
- `capstone_proj/gui/utils.py`: helper logic used by the GUI.
- `scripts/run_control_center.py`: launcher for the GUI app.
- `tests/`: unit tests for controller logic and input validation.
- `configs/`: experiment config templates.
- `docs/research/`: reading list and LeRobot/Hugging Face kickoff.
- `docs/roadmap/`: week-by-week execution structure.
- `docs/experiments/`: baseline experiment planning.
- `docs/ops/`: failure handling and intervention policy.
- `experiments/`: per-run logs/results summaries.
- `data/`: local dataset staging (ignored in Git).
- `artifacts/`: generated run artifacts (ignored in Git).

## 9. Git Workflow for Beginners (Branch, Commit, PR)

### One-time Git identity setup

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Daily workflow

1. Sync latest main:
```powershell
git checkout main
git pull origin main
```
2. Create a feature branch:
```powershell
git checkout -b feat/pid-right-arm-sign-tuning
```
3. Make changes.
4. Run tests:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
5. Commit:
```powershell
git add .
git commit -m "feat(control): tune right-arm mirror signs"
```
6. Push:
```powershell
git push -u origin feat/pid-right-arm-sign-tuning
```
7. Open PR on GitHub.

### Branch naming convention

- `feat/<short-topic>`
- `fix/<short-topic>`
- `docs/<short-topic>`
- `chore/<short-topic>`

Examples:

- `feat/lerobot-dataset-loader`
- `fix/mujoco-mesh-path`
- `docs/onboarding-readme`

### Commit message convention

Use:

`<type>(<scope>): <summary>`

Types:

- `feat` new functionality
- `fix` bug fix
- `docs` documentation only
- `test` tests only
- `refactor` code reorganization without behavior change
- `chore` tooling/maintenance

Examples:

- `feat(sim): add CLI arg for joint offset`
- `fix(xml): restore missing actuator include`
- `docs(readme): add beginner onboarding section`

## 10. Pull Request (PR) Structure

Use this structure in every PR description:

1. `Summary`
   - What changed in plain language.
2. `Why`
   - Problem being solved.
3. `Changes`
   - File-level bullets.
4. `How To Test`
   - Exact commands run locally.
5. `Evidence`
   - Test output, screenshots, or short clips if UI/visual behavior changed.
6. `Risks`
   - Anything uncertain or likely to break.
7. `Follow-ups`
   - Work intentionally left for later.

## 11. What Is Implemented vs Planned

### Implemented now

- baseline MuJoCo simulation run path.
- baseline PD controller with actuator clipping and bias compensation.
- starter unit tests for control logic.
- project folder structure for research + experiments.

### Planned next

- LeRobot/Hugging Face dataset and training pipeline integration.
- baseline experiment run with Pi0-style or GROOT-style approach.
- robust task success/failure labeling ("tell robot no" loop).

## 12. Common Errors and Fixes

### `python : The term 'python' is not recognized`

Python is not installed or not in PATH.
Reinstall Python and ensure `Add python.exe to PATH` is enabled.

### `externally-managed-environment` while installing packages

Install dependencies into `.venv` instead of global Python:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### MuJoCo XML include or mesh file errors

Check these files exist:

- `aloha.xml`
- `joint_position_actuators.xml`
- `keyframe_ctrl.xml`
- `assets/` with required mesh files

### Viewer does not appear

- Ensure you are running locally with graphics support.
- Remote/headless sessions may not support interactive OpenGL viewer.

## 13. Team Rules (Practical)

1. Never push directly to `main` unless explicitly approved.
2. Every code change should include a test or a reason why test is not possible.
3. Keep PRs small enough to review in one sitting.
4. Keep experiment configs versioned and reproducible.
5. Keep large data and generated artifacts out of Git.

## 14. Useful Commands Cheat Sheet

```powershell
# activate environment
.\.venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt

# run tests
.\.venv\Scripts\python.exe -m unittest discover -s tests

# run simulation
.\.venv\Scripts\python.exe startup.py --model aloha.xml --sim-seconds 60

# sync latest main
git checkout main
git pull origin main

# create new branch
git checkout -b feat/your-topic

# commit and push
git add .
git commit -m "feat(scope): summary"
git push -u origin feat/your-topic
```
