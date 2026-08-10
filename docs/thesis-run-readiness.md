# Thesis Run Readiness

## Draft Answers For Open Questions

1. Repository URL and pinned commit
   - Repository URL: `https://github.com/amadeus-central-hub/fom-chess.git`
   - Frozen baseline tag: `thesis-baseline-2026-08-10`
   - Frozen baseline commit: resolve via `git log -1 --format=%H thesis-baseline-2026-08-10`

2. Exact Copilot model designation
   - Still open until the first agent PR or Copilot UI metadata is captured.
   - Recommendation: record the exact string shown in Copilot or PR metadata at the first agent-generated PR.

3. Instruction file name
   - Repository now contains `.github/copilot-instructions.md`.
   - This is the single instruction file to reference in the thesis and repository setup.

4. Feature list F1-F5
   - F1: En passant capture
   - F2: Full castling legality checks
   - F3: Pawn promotion including underpromotion
   - F4: Checkmate and stalemate detection
   - F5: Draw by threefold repetition
   - Jira mapping: `UC-2` through `UC-6`, all linked to Epic `UC-1`.

5. Manual vs. agent order
   - Decision: perform the manual implementation before viewing the corresponding agent PR.
   - Rationale: this reduces contamination by the AI solution and keeps the comparison methodologically cleaner.

6. Pylint threshold
   - Repository is currently configured to `>= 9.00` in `.pylintrc`.
   - Recommendation: use `9.0` consistently in the thesis text, tickets, and evaluation tables.

7. Example ticket for chapter 4.1
   - Recommended example: `UC-2 Implement en passant capture`.

## Repository Checklist Status

- `.pylintrc` exists and is versioned.
- `.coveragerc` now exists for stable coverage measurement.
- `.github/copilot-instructions.md` now exists for fixed run instructions.
- Jira Epic `UC-1` and Stories `UC-2` to `UC-6` are created and standardized.
- Dedicated acceptance-oriented readiness tests now exist for F1 to F5.
- Execution order is fixed to `manual first`, then `agent`.
- Operational run checklist and data-capture template are documented in `docs/thesis-run-checklist.md`.

## Frozen Baseline Measurement

- Baseline tag: `thesis-baseline-2026-08-10`
- Baseline commit: resolve via `git log -1 --format=%H thesis-baseline-2026-08-10`
- Baseline interpreter used for the authoritative run: project `.venv`, Python `3.13.2`
- Baseline `pytest` result: `56 passed, 1 xfailed` in `0.61s`
- Baseline coverage result: `86%` total in `1.65s`
- Baseline open item intentionally visible in the suite: `UC-6` / threefold repetition remains `xfail`

## Supporting Run Documents

- Detailed operational checklist: `docs/thesis-run-checklist.md`
- Printable short form: `docs/thesis-run-checklist-printable.md`
- Standardized per-run results template: `docs/thesis-run-results-template.md`
- CSV raw-data table: `docs/thesis-run-results.csv`
- Baseline freeze procedure: `docs/thesis-baseline-freeze.md`
- First manual-run worksheet: `docs/uc-2-manual-run-sheet.md`

## Ticket List

- `UC-1` Epic: FIDE-Correct Special Rules and Endgame Detection
- `UC-2` Story: Implement en passant capture
- `UC-3` Story: Implement full castling legality checks
- `UC-4` Story: Implement pawn promotion including underpromotion
- `UC-5` Story: Detect checkmate and stalemate
- `UC-6` Story: Detect draw by threefold repetition
