# Thesis Run Results Template

## Purpose

Use this template once per measured run so that evaluation and results can be written in a standardized way afterward.

## Metric Definitions

- `Passed First Try`: `yes` if the first full validation after implementation already satisfies the ticket without additional repair.
- `Final Pass`: `yes` if the run ends with all required validations green under the thesis rules.
- `Coverage %`: total coverage shown by `pytest --cov=src --cov-report=term-missing`.
- `Pylint Score`: the final numeric score reported by Pylint for the predefined command.
- `Files Changed`: count of files modified for the run result.
- `Added Lines` and `Removed Lines`: use the final diff statistics for the run branch against the fixed baseline.
- `Human Interventions`: count each human code correction, prompt correction, or manual repair step after the initial implementation attempt.
- `Result`: use one of `pass without rework`, `pass with minor rework`, `pass with major rework`, `fail`, or `stopped`.

## Standard Commands

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing
.\.venv\Scripts\python.exe -m pylint src tests
git diff --shortstat BASELINE..HEAD
```

Replace `BASELINE` with the frozen baseline commit or tag.

## Per-Run Form

### Run Metadata

| Field | Value |
| --- | --- |
| Run ID |  |
| Ticket |  |
| Mode | Manual / Agent |
| Baseline Commit or Tag |  |
| Working Branch |  |
| Start Timestamp |  |
| End Timestamp |  |
| Net Minutes |  |
| Interruptions |  |

### Implementation Summary

| Field | Value |
| --- | --- |
| Goal of the run |  |
| Files changed |  |
| Added lines |  |
| Removed lines |  |
| Human interventions |  |
| Prompt text used | n/a for manual |
| Model designation | n/a for manual |

### Validation Summary

| Field | Value |
| --- | --- |
| Ticket-specific test command |  |
| Ticket-specific tests result |  |
| Full pytest result |  |
| Coverage % |  |
| Pylint command |  |
| Pylint score |  |
| Passed first try |  |
| Final pass |  |

### Requirements Check

| Field | Value |
| --- | --- |
| Acceptance criteria satisfied |  |
| DoD satisfied |  |
| Deviations from ticket |  |
| Remaining open points |  |

### Evidence References

| Field | Value |
| --- | --- |
| Final commit hash |  |
| PR link or review artifact |  |
| Jira issue key |  |
| Validation log location |  |
| Additional notes |  |

## Short Narrative Template

Use the following structure to write a consistent run summary.

```text
Run [Run ID] addressed [Ticket] in [Mode] mode from baseline [Baseline Commit or Tag].
The implementation required [Net Minutes] minutes and resulted in [Files Changed] changed files,
[Added Lines] added lines, and [Removed Lines] removed lines.
Validation ended with [Full pytest result], [Coverage %] total coverage, and a Pylint score of [Pylint Score].
The run [passed first try / required rework] and the final result was [Result].
Open points: [Remaining open points].
```

## Compact Comparison Table

Copy this table when comparing all runs in the evaluation chapter.

| Run ID | Ticket | Mode | Net Minutes | Passed First Try | Final Pass | Coverage % | Pylint Score | Files Changed | Added | Removed | Human Interventions | Result |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| R01 | UC-2 | Manual |  |  |  |  |  |  |  |  | 0 |  |
| R02 | UC-2 | Agent |  |  |  |  |  |  |  |  |  |  |
| R03 | UC-3 | Manual |  |  |  |  |  |  |  |  | 0 |  |
| R04 | UC-3 | Agent |  |  |  |  |  |  |  |  |  |  |
| R05 | UC-4 | Manual |  |  |  |  |  |  |  |  | 0 |  |
| R06 | UC-4 | Agent |  |  |  |  |  |  |  |  |  |  |
| R07 | UC-5 | Manual |  |  |  |  |  |  |  |  | 0 |  |
| R08 | UC-5 | Agent |  |  |  |  |  |  |  |  |  |  |
| R09 | UC-6 | Manual |  |  |  |  |  |  |  |  | 0 |  |
| R10 | UC-6 | Agent |  |  |  |  |  |  |  |  |  |  |

## Standardization Rules

- Count only net working time, not unrelated interruptions.
- Use the same validation commands for every run.
- For agent runs, preserve the first raw output before any manual repair.
- Record manual fixes after agent output as interventions, not as hidden cleanup.
- Keep ticket scope strict: one ticket, one run pair, one baseline.