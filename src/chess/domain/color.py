"""Color enum used throughout the domain."""

from __future__ import annotations

from enum import Enum


class Color(Enum):
    """Player color."""

    WHITE = "white"
    BLACK = "black"

    @property
    def opponent(self) -> "Color":
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    @property
    def forward_direction(self) -> int:
        """Row index delta when this color's pawn moves one step forward.

        In the internal board representation row index 0 is rank 8 (black's back rank)
        and row index 7 is rank 1 (white's back rank), so white moves "up" (-1) and
        black moves "down" (+1).
        """
        return -1 if self is Color.WHITE else 1
