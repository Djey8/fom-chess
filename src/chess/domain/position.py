"""Position value object: a single square on the board."""

from __future__ import annotations

from dataclasses import dataclass

FILES = "abcdefgh"
RANKS = "12345678"


@dataclass(frozen=True)
class Position:
    """Immutable board coordinate.

    Attributes:
        row: Internal row index (0 = rank 8, 7 = rank 1).
        col: Internal column index (0 = file a, 7 = file h).
    """

    row: int
    col: int

    def __post_init__(self) -> None:
        if not (0 <= self.row <= 7 and 0 <= self.col <= 7):
            raise ValueError(f"Position out of bounds: row={self.row}, col={self.col}")

    # ---- constructors -------------------------------------------------
    @classmethod
    def from_algebraic(cls, square: str) -> "Position":
        """Build from algebraic notation, e.g. ``"e4"``."""
        if len(square) != 2:
            raise ValueError(f"Invalid square: {square!r}")
        file_ch, rank_ch = square[0].lower(), square[1]
        if file_ch not in FILES or rank_ch not in RANKS:
            raise ValueError(f"Invalid square: {square!r}")
        col = FILES.index(file_ch)
        row = 7 - RANKS.index(rank_ch)  # rank '1' -> row 7
        return cls(row=row, col=col)

    # ---- accessors ----------------------------------------------------
    @property
    def file(self) -> str:
        return FILES[self.col]

    @property
    def rank(self) -> str:
        return RANKS[7 - self.row]

    @property
    def algebraic(self) -> str:
        return f"{self.file}{self.rank}"

    def offset(self, drow: int, dcol: int) -> "Position | None":
        """Return neighbouring position or ``None`` if out of bounds."""
        new_row, new_col = self.row + drow, self.col + dcol
        if 0 <= new_row <= 7 and 0 <= new_col <= 7:
            return Position(new_row, new_col)
        return None

    def __str__(self) -> str:
        return self.algebraic
