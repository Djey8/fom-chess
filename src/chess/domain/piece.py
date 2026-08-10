"""Piece model: type enum and immutable Piece value object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .color import Color


class PieceType(Enum):
    PAWN = "P"
    KNIGHT = "N"
    BISHOP = "B"
    ROOK = "R"
    QUEEN = "Q"
    KING = "K"


@dataclass(frozen=True)
class Piece:
    """A chess piece: type + color."""

    type: PieceType
    color: Color

    @property
    def symbol(self) -> str:
        """Single-letter symbol. Uppercase = white, lowercase = black."""
        letter = self.type.value
        return letter if self.color is Color.WHITE else letter.lower()

    @classmethod
    def from_symbol(cls, symbol: str) -> "Piece":
        if symbol.upper() not in {t.value for t in PieceType}:
            raise ValueError(f"Unknown piece symbol: {symbol!r}")
        color = Color.WHITE if symbol.isupper() else Color.BLACK
        return cls(type=PieceType(symbol.upper()), color=color)

    def __str__(self) -> str:
        return self.symbol
