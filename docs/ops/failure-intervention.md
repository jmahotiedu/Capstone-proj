# Failure Intervention: "Tell the Robot No"

## Problem

The system needs a clear way to reject incorrectly completed tasks and prevent reinforcing bad behavior.

## Practical Control Loop

1. Policy proposes action.
2. Safety checks run before execution.
3. Action executes in sim/hardware.
4. Post-condition checks verify task correctness.
5. If failed, mark trajectory with explicit negative label and trigger recovery routine.

## What to Track

- `task_success`: boolean.
- `failure_reason`: categorical code.
- `intervention_source`: human, rule-based, or automated checker.
- `recovery_action`: reset, replan, or stop.

## Immediate Next Step

Define one task-specific failure checker in simulation first (for example, wrong wrench bin) and require it in every experiment run.
