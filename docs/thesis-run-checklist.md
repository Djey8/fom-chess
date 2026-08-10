# Thesis Run Checklist

## Scope

This checklist is the operational procedure for the measured thesis runs of:

1. `UC-2` En passant capture
2. `UC-3` Full castling legality checks
3. `UC-4` Pawn promotion including underpromotion
4. `UC-5` Checkmate and stalemate detection
5. `UC-6` Draw by threefold repetition

The execution order is fixed:

1. Manual implementation run
2. Agent-assisted implementation run

## Global Freeze Before The First Measured Run

- [ ] Confirm the repository baseline commit or tag is fixed and recorded.
- [ ] Confirm Appendix 1 and Appendix 2 content is finalized and frozen.
- [ ] Confirm `.github/copilot-instructions.md` is the only active Copilot instruction file.
- [ ] Confirm the Jira scope is fixed to Epic `UC-1` with Stories `UC-2` to `UC-6`.
- [ ] Confirm the measurement rules are fixed before implementation begins.
- [ ] Confirm the developer environment and `.venv` are ready.
- [ ] Confirm no uncommitted unrelated changes are present.

## Baseline Run Before Any Feature Work

- [ ] Activate the project environment.
- [ ] Run `pytest` for the full suite.
- [ ] Run `pytest --cov=src --cov-report=term-missing`.
- [ ] Record total passed, failed, xfailed, and coverage percentage.
- [ ] Save the baseline output in the thesis notes or appendix material.
- [ ] Record the exact baseline commit or tag used for all runs.

## Common Rules For Every Measured Run

- [ ] Start from the same clean baseline commit or tag.
- [ ] Work on exactly one Jira story at a time.
- [ ] Do not mix multiple feature tickets in one measured run.
- [ ] Record the start timestamp before reading or changing code.
- [ ] Record the end timestamp after the final validation run.
- [ ] Record any interruptions separately.
- [ ] Keep all commands, prompts, review notes, and outcomes for later evidence.
- [ ] Run validation only with the predefined project checks.

## Manual Run Checklist Per Ticket

Use this sequence separately for `UC-2`, `UC-3`, `UC-4`, `UC-5`, and `UC-6`.

### Preparation

- [ ] Reset the workspace to the fixed baseline commit or tag.
- [ ] Create or checkout the manual branch for the ticket.
- [ ] Open the Jira ticket and read description, acceptance criteria, and DoD text.
- [ ] Start the time log.

### Implementation

- [ ] Implement the ticket without looking at any agent-generated solution.
- [ ] Add or update tests required by the ticket.
- [ ] Keep changes within the repository constraints and architecture.

### Validation

- [ ] Run the ticket-relevant tests first.
- [ ] Run the full `pytest` suite.
- [ ] Run `pytest --cov=src --cov-report=term-missing`.
- [ ] Run `pylint src tests` or the thesis-defined Pylint command.
- [ ] Record whether the run meets acceptance criteria and DoD.

### Evidence Collection

- [ ] Record elapsed implementation time in minutes.
- [ ] Record number of changed files.
- [ ] Record lines added and removed.
- [ ] Record test status and coverage.
- [ ] Record Pylint result.
- [ ] Save the final commit hash.

### Closure

- [ ] Create the manual PR or equivalent review artifact.
- [ ] Record review findings if a review step is part of the study.
- [ ] Mark the manual run as complete before starting the agent run.

## Agent Run Checklist Per Ticket

Use this sequence separately for `UC-2`, `UC-3`, `UC-4`, `UC-5`, and `UC-6`.

### Preparation

- [ ] Reset the workspace to the same fixed baseline commit or tag.
- [ ] Create or checkout the agent branch for the ticket.
- [ ] Open the same Jira ticket used for the manual run.
- [ ] Confirm the active instruction file is `.github/copilot-instructions.md`.
- [ ] Start the time log.

### Agent Execution

- [ ] Submit the implementation request for exactly one ticket.
- [ ] Save the exact prompt text used.
- [ ] Record the Copilot model designation shown in the tool or PR metadata.
- [ ] Preserve agent comments, intermediate outputs, and generated diffs.
- [ ] Do not silently fix generated code without recording the intervention.

### Validation

- [ ] Run the ticket-relevant tests first.
- [ ] Run the full `pytest` suite.
- [ ] Run `pytest --cov=src --cov-report=term-missing`.
- [ ] Run `pylint src tests` or the thesis-defined Pylint command.
- [ ] Record whether the unmodified agent result passed immediately.
- [ ] If manual repair is needed, record each intervention separately.

### Evidence Collection

- [ ] Record elapsed total time in minutes.
- [ ] Record pure agent runtime separately if observable.
- [ ] Record human intervention count.
- [ ] Record number of changed files.
- [ ] Record lines added and removed.
- [ ] Record test status and coverage.
- [ ] Record Pylint result.
- [ ] Save the final commit hash.
- [ ] Save the PR link if the agent created one.

### Closure

- [ ] Create the final agent PR or equivalent review artifact.
- [ ] Record review findings if a review step is part of the study.
- [ ] Mark whether the agent run satisfied the ticket without rework, with minor rework, or only after larger repair.

## Recommended Command Set

Use one fixed command set across all runs.

```powershell
pytest
pytest --cov=src --cov-report=term-missing
pylint src tests
```

If a narrower ticket-specific test command is also used, record it consistently for every ticket.

## Time Log Template

Fill one row per measured run.

| Run ID | Ticket | Mode | Baseline Commit | Branch | Start | End | Net Minutes | Interruptions | Result |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| R01 | UC-2 | Manual |  |  |  |  |  |  |  |
| R02 | UC-2 | Agent |  |  |  |  |  |  |  |
| R03 | UC-3 | Manual |  |  |  |  |  |  |  |
| R04 | UC-3 | Agent |  |  |  |  |  |  |  |
| R05 | UC-4 | Manual |  |  |  |  |  |  |  |
| R06 | UC-4 | Agent |  |  |  |  |  |  |  |
| R07 | UC-5 | Manual |  |  |  |  |  |  |  |
| R08 | UC-5 | Agent |  |  |  |  |  |  |  |
| R09 | UC-6 | Manual |  |  |  |  |  |  |  |
| R10 | UC-6 | Agent |  |  |  |  |  |  |  |

## Data Capture Template For Thesis Table 2

Fill one row per measured run.

| Run ID | Ticket | Mode | Passed First Try | Final Pass | Coverage % | Pylint Score | Files Changed | Added Lines | Removed Lines | Human Interventions | PR Created | Notes |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| R01 | UC-2 | Manual |  |  |  |  |  |  |  | 0 | n/a |  |
| R02 | UC-2 | Agent |  |  |  |  |  |  |  |  |  |  |
| R03 | UC-3 | Manual |  |  |  |  |  |  |  | 0 | n/a |  |
| R04 | UC-3 | Agent |  |  |  |  |  |  |  |  |  |  |
| R05 | UC-4 | Manual |  |  |  |  |  |  |  | 0 | n/a |  |
| R06 | UC-4 | Agent |  |  |  |  |  |  |  |  |  |  |
| R07 | UC-5 | Manual |  |  |  |  |  |  |  | 0 | n/a |  |
| R08 | UC-5 | Agent |  |  |  |  |  |  |  |  |  |  |
| R09 | UC-6 | Manual |  |  |  |  |  |  |  | 0 | n/a |  |
| R10 | UC-6 | Agent |  |  |  |  |  |  |  |  |  |  |

## Minimal Evidence Package Per Run

- [ ] Jira ticket snapshot
- [ ] Branch name
- [ ] Final commit hash
- [ ] Validation command outputs
- [ ] Coverage result
- [ ] Pylint result
- [ ] PR link or review artifact
- [ ] Time log entry
- [ ] Short notes on blockers, rework, and deviations

## Interpretation Rules To Freeze Before Analysis

- [ ] Define what counts as a human intervention in agent runs.
- [ ] Define whether documentation-only edits count toward effort.
- [ ] Define whether prompt refinement counts as rework.
- [ ] Define whether review fixes are included in measured time.
- [ ] Define whether xfailed tests are treated as open target behavior or failure.
- [ ] Define the exact rule for successful completion of `UC-6` given the current readiness baseline.