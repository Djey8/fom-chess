# Chess MVP

A console-based chess game in Python, built with a clean layered architecture
so that the rules engine is fully testable and the presentation layer is
swappable (console today, GUI tomorrow).

## Features

- Full standard chess rules: pawn, knight, bishop, rook, queen, king.
- Special moves: castling (both sides), en passant, pawn promotion.
- Move legality validation — moves that leave your own king in check are
  rejected.
- Check, checkmate, and stalemate detection.
- Algebraic notation (SAN) and simple coordinate notation (e.g. `e2e4`).
- Colored Unicode board rendering with automatic ASCII fallback on consoles
  that cannot encode Unicode.

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
| `<move>` | Play a move. Accepts SAN (`e4`, `Nf3`, `exd5`, `O-O`, `e8=Q`) or coordinate form (`e2e4`, `e7e8q`). |
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
