# Contributing Guide

This document explains exactly how to contribute to this project, even if you are new to Git and pull requests.

## 1. Goal of This Workflow

The workflow exists to keep project changes:

- reproducible
- reviewable
- safe for teammates
- easy to test

## 2. Prerequisites

You should already have:

- Git installed
- Python 3.12+ installed
- VS Code installed
- this repository cloned locally

If not, follow setup in `README.md`.

## 3. First-Time Local Setup

From project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 4. Branch Workflow (Required)

Never work directly on `main`.

For every task:

1. Sync local `main`
```powershell
git checkout main
git pull origin main
```
2. Create feature branch
```powershell
git checkout -b feat/short-topic-name
```
3. Make your changes.
4. Run tests.
5. Commit and push branch.
6. Open Pull Request to `main`.

## 5. Branch Naming Convention

Use one of these prefixes:

- `feat/` new feature
- `fix/` bug fix
- `docs/` documentation
- `test/` tests
- `refactor/` non-functional restructure
- `chore/` maintenance/tooling

Examples:

- `feat/lerobot-dataset-bootstrap`
- `fix/aloha-mesh-path`
- `docs/update-onboarding-guide`

## 6. Commit Message Convention

Format:

`type(scope): summary`

Examples:

- `feat(sim): add model path CLI argument`
- `fix(control): validate desired vector shape`
- `docs(readme): expand beginner setup steps`
- `test(control): add right-arm sign coverage`

Guidelines:

- keep summary under 72 characters if possible
- use imperative voice (`add`, `fix`, `update`)
- one logical change per commit

## 7. Required Local Checks Before PR

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

If simulation code changed, also run:

```powershell
.\.venv\Scripts\python.exe startup.py --model aloha.xml --sim-seconds 10
```

If a check fails, do not open PR yet.

## 8. Push and Open PR

Push branch:

```powershell
git add .
git commit -m "feat(scope): summary"
git push -u origin feat/short-topic-name
```

Then open the GitHub PR page and fill in all sections from the PR template.

## 9. Pull Request Expectations

Every PR should include:

- clear summary of what changed
- clear reason for change
- exact test commands run
- risks or limitations
- follow-up tasks if needed

Keep PRs small enough that a reviewer can fully review in one pass.

## 10. XML and MuJoCo Change Rules

When editing `aloha.xml` or related files:

- validate that included files still exist
- do not rename mesh files unless references are updated
- keep units and joint semantics consistent
- run simulation after each meaningful XML edit

Files that must remain consistent:

- `aloha.xml`
- `joint_position_actuators.xml`
- `keyframe_ctrl.xml`
- `assets/*`

## 11. Data and Artifact Rules

Do not commit:

- large datasets in `data/`
- generated run outputs in `artifacts/`
- temporary experiment output files in `experiments/`

These are intentionally ignored via `.gitignore`.

## 12. Review and Merge Policy

- At least one teammate should review your PR.
- Address all review comments before merge.
- Prefer squash merge unless team agrees otherwise.
- Do not force push to shared branches unless coordinated.

## 13. Beginner FAQ

### I edited the wrong branch. What do I do?

Create a new branch from your current state:

```powershell
git checkout -b fix/moved-work-to-correct-branch
```

Then open PR from that branch.

### My `git push` says permission denied.

You need collaborator access, or you must fork the repo and open a PR from your fork.

### I forgot to pull main before starting.

Run:

```powershell
git checkout main
git pull origin main
git checkout your-branch
git rebase main
```

If conflicts appear, resolve them and re-run tests.

## 14. Where to Put Work

- research summaries: `docs/research/`
- roadmap updates: `docs/roadmap/`
- experiment plans: `docs/experiments/`
- operational checklists: `docs/ops/`
- control/simulation code: `capstone_proj/`
- tests: `tests/`

If unsure where a file belongs, open a PR draft and ask in the PR notes.

