# LeRobot + Hugging Face Kickoff

## Why This Matters

LeRobot can standardize dataset/policy/training plumbing so experiments stay reproducible across teammates.

## Integration Goals

- Standardize dataset loading and preprocessing.
- Standardize training config management.
- Standardize evaluation logging.

## Near-Term Deliverables

- `docs/research/reading-list.md` completed with paper summaries.
- One dataset selected and pinned for baseline training.
- One baseline training run completed with saved configs and metrics.
- One evaluation script that can score a run and emit success/failure breakdown.

## Decision Gates

- Gate 1: Dataset quality and task fit approved.
- Gate 2: Baseline policy train/eval pipeline runs end-to-end.
- Gate 3: Intervention labeling available for failure cases.
