# Chess MVP

A console-based chess game in Python, built with a clean layered architecture
so that the rules engine is fully testable and the presentation layer is
swappable (console today, GUI tomorrow).

> **Thesis baseline notice:** the tag `thesis-baseline-2026-08-10` marks the
> frozen starting point for a comparative study of manual vs. Copilot-agent
> implementation of five FIDE special-rule/endgame-detection tickets
> (`UC-2`–`UC-6`, epic `UC-1`). As of that baseline, castling, en passant,
> pawn promotion, and checkmate/stalemate detection are **intentionally not
> implemented** — see `tests/application/test_ticket_readiness.py` for the
> readiness suite (5 xfailed) that documents this. Full implementation
> history predating the baseline is preserved on the
> `full-implementation-reference` branch.

## Features (baseline)

- Basic chess piece movement: pawn (incl. two-square first move), knight,
  bishop, rook, queen, king (one square, no castling).
- Move legality validation — moves that leave your own king in check are
  rejected.
- Check detection (`+` display), 50-move draw rule.
- Algebraic notation (SAN) and simple coordinate notation (e.g. `e2e4`).
- Colored Unicode board rendering with automatic ASCII fallback on consoles
  that cannot encode Unicode.
- **Not yet implemented (thesis tickets `UC-2`–`UC-6`):** castling, en
  passant, pawn promotion, checkmate/stalemate detection, threefold
  repetition.

## Requirements

- Python 3.10+

## Setup

```powershell
# From the repository root
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
```

## Run the game

```powershell
python -m chess.main
```

### In-game commands

| Command | Effect |
|---|---|
| `<move>` | Play a move. Accepts SAN (`e4`, `Nf3`, `exd5`) or coordinate form (`e2e4`). |
| `board`  | Re-render the current board. |
| `moves`  | List all legal moves for the side to move (coordinate form). |
| `resign` | Resign the game. |
| `help`   | Show command help. |
| `quit`   | Exit. |

## Run the tests

```powershell
python -m pytest
```

Coverage-focused run:

```powershell
python -m pytest --cov=chess --cov-report=term-missing
```

Lint-focused run:

```powershell
python -m pylint src/chess/domain/rules.py src/chess/application/game.py
```

## Documentation

Architecture diagrams, current project status, and the thesis study
documentation (Jira↔GitHub↔Copilot automation, run checklists, ticket pack)
are maintained outside this repository, not in `docs/`.
