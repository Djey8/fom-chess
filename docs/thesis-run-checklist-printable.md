# Thesis Run Checklist Printable

## Fixed Setup

- [ ] Baseline commit or tag fixed
- [ ] Appendix 1 frozen
- [ ] Appendix 2 frozen
- [ ] `.github/copilot-instructions.md` confirmed as single instruction file
- [ ] Epic `UC-1` and tickets `UC-2` to `UC-6` confirmed
- [ ] Run order fixed: `manual first`, then `agent`

## Baseline Reference

- Tag: `thesis-baseline-2026-08-10`
- Commit: resolve via `git log -1 --format=%H thesis-baseline-2026-08-10`
- Authoritative environment: `.venv` / Python `3.13.2`
- `pytest`: `56 passed, 1 xfailed`
- Coverage: `86%`

## Per-Run Short Checklist

Run ID: ____________________

Ticket: ____________________

Mode: `Manual` / `Agent`

Branch: ____________________

Start: ____________________

End: ____________________

- [ ] Clean baseline checked out
- [ ] Exactly one ticket processed
- [ ] Time log started before implementation
- [ ] Tests added or updated if required
- [ ] Ticket-specific validation run
- [ ] Full `pytest` run
- [ ] Coverage run
- [ ] Pylint run
- [ ] Acceptance criteria checked
- [ ] DoD checked
- [ ] Final commit hash recorded
- [ ] PR or review artifact recorded
- [ ] Result template completed

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing
.\.venv\Scripts\python.exe -m pylint src tests
```

## Final Outcome

Result: ____________________

Net minutes: ____________________

Coverage %: ____________________

Pylint score: ____________________

Files changed: ____________________

Added lines: ____________________

Removed lines: ____________________

Human interventions: ____________________

Notes: ________________________________________________________________

Notes: ________________________________________________________________

Notes: ________________________________________________________________