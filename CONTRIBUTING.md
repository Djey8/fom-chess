# Contributing

Thanks for improving the chess MVP. This short guide keeps the codebase
consistent.

## Environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
```

## Architectural rules

The project uses a layered architecture (see
[doc/architecture.md](doc/architecture.md)). Dependencies must always point
**downward**:

```
presentation → application → domain
```

- **Never** import `chess.presentation` from `chess.application` or
  `chess.domain`.
- **Never** import `chess.application` from `chess.domain`.
- No `print()` or `input()` inside `chess.domain` or `chess.application`.
- All rule decisions live in `chess.domain`. The presentation layer may
  only display rule outputs, not compute them.

## Coding style

- PEP 8, `snake_case` for functions/variables, `PascalCase` for classes,
  `UPPER_SNAKE_CASE` for constants.
- Type hints required on all new public functions and dataclasses.
- English for identifiers, comments, and docstrings.
- Prefer small, focused functions. Do not reintroduce the single-file
  god object.

## Tests

- Add or update tests alongside every change.
- Domain-layer logic must be unit-tested in isolation (no I/O).
- For application-layer bugs, add a regression test that fails before the
  fix and passes afterwards.
- Run `python -m pytest` before opening a PR.
- Run `python -m pylint <changed files>` and keep the score at or above `9.00`.

## Commit / PR checklist

- [ ] Tests added or updated.
- [ ] `python -m pytest` is green.
- [ ] No I/O leaked into domain/application layers.
- [ ] Docs updated if public behavior, setup, or structure changed.
