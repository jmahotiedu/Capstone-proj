# Experiments Directory

Use this folder for reproducible experiment runs.

## Required Artifacts per Experiment

- Config snapshot copied from `configs/experiment-template.json`.
- Training/eval logs.
- Metrics summary with:
  - success rate
  - intervention count
  - failure reason distribution
- Notes on observed failure modes and next changes.

## Naming Convention

`YYYY-MM-DD_<task>_<model>_<short-tag>`

Example: `2026-02-12_wrench-sort_pi0_baseline`
