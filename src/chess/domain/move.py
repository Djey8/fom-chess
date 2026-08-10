"""Move value object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .piece import Piece, PieceType
from .position import Position


class MoveKind(Enum):
    NORMAL = "normal"
    CAPTURE = "capture"
    DOUBLE_PAWN = "double_pawn"
    EN_PASSANT = "en_passant"
    CASTLE_KINGSIDE = "castle_kingside"
    CASTLE_QUEENSIDE = "castle_queenside"
    PROMOTION = "promotion"
    PROMOTION_CAPTURE = "promotion_capture"


@dataclass(frozen=True)
class Move:
    """A single move decision.

    ``captured`` stores the captured piece if any (including for en passant).
    ``promotion`` is set when a pawn promotes.
    """

    piece: Piece
    origin: Position
    target: Position
    kind: MoveKind = MoveKind.NORMAL
    captured: Optional[Piece] = None
    promotion: Optional[PieceType] = None

    @property
    def is_capture(self) -> bool:
        return self.captured is not None

    @property
    def is_castle(self) -> bool:
        return self.kind in (MoveKind.CASTLE_KINGSIDE, MoveKind.CASTLE_QUEENSIDE)

    @property
    def is_promotion(self) -> bool:
        return self.promotion is not None
