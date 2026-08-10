# Thesis Baseline Freeze

## Purpose

Use this note to freeze the exact starting point before the measured manual and agent runs begin.

## Recommended Baseline Identifier

- Frozen baseline tag: `thesis-baseline-2026-08-10`
- Frozen baseline commit: resolve via `git log -1 --format=%H thesis-baseline-2026-08-10`

## Freeze Decision

The repository is now frozen with the baseline tag below. Use this identifier consistently in the thesis text.

1. Commit: resolve via `git log -1 --format=%H thesis-baseline-2026-08-10`
2. Tag: `thesis-baseline-2026-08-10`

## Recommended Procedure

The freeze has already been performed with a snapshot commit followed by an annotated tag.

```powershell
git rev-parse thesis-baseline-2026-08-10
git log -1 --format=%H thesis-baseline-2026-08-10
```

If you need to recreate the tag locally, point it to the frozen commit above.

```powershell
git tag -a thesis-baseline-2026-08-10 -m "Frozen baseline for thesis runs" <BASELINE_COMMIT>
git rev-parse thesis-baseline-2026-08-10
```

## Freeze Record

| Field | Value |
| --- | --- |
| Final baseline commit | Resolve via `git log -1 --format=%H thesis-baseline-2026-08-10` |
| Final baseline tag | thesis-baseline-2026-08-10 |
| Freeze date | 2026-08-10 |
| Frozen by | GitHub Copilot Coding Agent |
| Notes |  |

## Thesis Wording Template

```text
All measured runs were executed from the frozen repository baseline [BASELINE TAG] at commit [BASELINE COMMIT].
The baseline was fixed before any measured implementation run and used unchanged for both the manual and the agent-assisted conditions.
```