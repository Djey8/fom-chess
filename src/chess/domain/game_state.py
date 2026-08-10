"""Game state: whose turn, castling rights, en passant target, history."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .color import Color
from .move import Move
from .position import Position


@dataclass
class CastlingRights:
    kingside: bool = True
    queenside: bool = True


@dataclass
class GameState:
    turn: Color = Color.WHITE
    white_castling: CastlingRights = field(default_factory=CastlingRights)
    black_castling: CastlingRights = field(default_factory=CastlingRights)
    en_passant_target: Optional[Position] = None
    halfmove_clock: int = 0  # for 50-move rule (not enforced in MVP)
    fullmove_number: int = 1
    history: list[Move] = field(default_factory=list)

    def castling_rights(self, color: Color) -> CastlingRights:
        return self.white_castling if color is Color.WHITE else self.black_castling

    def clone(self) -> "GameState":
        return GameState(
            turn=self.turn,
            white_castling=CastlingRights(
                self.white_castling.kingside, self.white_castling.queenside
            ),
            black_castling=CastlingRights(
                self.black_castling.kingside, self.black_castling.queenside
            ),
            en_passant_target=self.en_passant_target,
            halfmove_clock=self.halfmove_clock,
            fullmove_number=self.fullmove_number,
            history=list(self.history),
        )
