# Baseline Model Plan: Pi0 vs GROOT-style

## Objective

Run one pre-existing dataset through an initial baseline training pipeline to establish a reproducible benchmark.

## Candidate Baselines

- Pi0-inspired baseline for general-purpose policy pretraining ideas.
- GROOT-style baseline for manipulation-heavy pipelines.

## First Implementation Strategy

- Start with a single training baseline, not both at once.
- Prioritize whichever has cleaner dataset and tooling compatibility.
- Keep simulation and evaluation harness fixed while swapping model backends.

## Minimum Experiment Template

- Dataset identifier and version pinned.
- Train/validation split pinned.
- Seed pinned.
- Runtime configuration saved to `artifacts/`.
- Output metrics:
  - success rate
  - completion time
  - intervention count
  - failure type counts

## Candidate Task Ideas

- Sorting wrenches by size.
- Cable routing and insertion alignment.
- Bimanual pick-and-place with orientation constraints.

## Exit Criteria for First Baseline

- End-to-end run reproducible by another teammate.
- Metrics recorded in a comparable format.
- At least one clear failure pattern identified for iteration.
