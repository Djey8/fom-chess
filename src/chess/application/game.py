"""Game controller: orchestrates board, state, and rules."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..domain.board import Board
from ..domain.color import Color
from ..domain.game_state import GameState
from ..domain.move import Move
from ..domain.piece import PieceType
from ..domain.position import Position
from ..domain.rules import (
    apply_move,
    generate_legal_moves,
    is_in_check,
)

_logger = logging.getLogger(__name__)


class GameResult(Enum):
    ONGOING = "ongoing"
    WHITE_WINS = "white_wins"
    BLACK_WINS = "black_wins"
    STALEMATE = "stalemate"
    DRAW = "draw"


@dataclass
class MoveOutcome:
    move: Move
    gave_check: bool
    result: GameResult


class IllegalMoveError(ValueError):
    """Raised when a caller tries to make a move that is not legal."""


class Game:
    """High-level chess game controller."""

    def __init__(self, board: Optional[Board] = None, state: Optional[GameState] = None) -> None:
        self.board = board if board is not None else Board.standard()
        self.state = state if state is not None else GameState()
        self._result: GameResult = GameResult.ONGOING
        self._position_counts: Counter = Counter()
        # Record the starting position as the first occurrence.
        initial_snapshot = self.state.position_snapshot(self.board.position_key())
        self._position_counts[initial_snapshot] += 1

    # ---- public API ---------------------------------------------------
    @property
    def turn(self) -> Color:
        return self.state.turn

    @property
    def result(self) -> GameResult:
        return self._result

    def is_over(self) -> bool:
        return self._result is not GameResult.ONGOING

    def legal_moves(self, color: Optional[Color] = None) -> list[Move]:
        return generate_legal_moves(self.board, color or self.state.turn, self.state)

    def legal_moves_from(self, origin: Position) -> list[Move]:
        return [m for m in self.legal_moves() if m.origin == origin]

    def find_legal_move(
        self,
        origin: Position,
        target: Position,
        promotion: Optional[PieceType] = None,
    ) -> Optional[Move]:
        """Find the unique legal move matching origin/target (and promotion, if relevant)."""
        candidates = [
            m
            for m in self.legal_moves()
            if m.origin == origin and m.target == target
        ]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        # Promotion ambiguity: require an explicit choice.
        for m in candidates:
            if m.promotion == promotion:
                return m
        return None

    def make_move(self, move: Move) -> MoveOutcome:
        """Apply ``move`` after validating it against the current legal move list."""
        if self.is_over():
            raise IllegalMoveError("The game is already over.")
        legal = self.legal_moves()
        # Match by structural equality (frozen dataclass).
        if move not in legal:
            # Allow matching by key fields if promotion types differ in defaults.
            match = next(
                (
                    m
                    for m in legal
                    if m.origin == move.origin
                    and m.target == move.target
                    and m.promotion == move.promotion
                ),
                None,
            )
            if match is None:
                raise IllegalMoveError(
                    f"Illegal move: {move.origin}->{move.target}"
                )
            move = match

        self._apply(move)
        return self._finalize_turn(move)

    # ---- internals ----------------------------------------------------
    def _apply(self, move: Move) -> None:
        # NOTE (thesis baseline `thesis-baseline-2026-08-10`): castling-rights
        # revocation (UC-3) and en-passant-target lifecycle tracking (UC-2)
        # are intentionally not implemented yet.
        self.state.en_passant_target = None

        # Halfmove clock — reset on pawn move or capture, increment otherwise
        if move.piece.type is PieceType.PAWN or move.is_capture:
            self.state.halfmove_clock = 0
        else:
            self.state.halfmove_clock += 1

        apply_move(self.board, move)
        self.state.history.append(move)

        if self.state.turn is Color.BLACK:
            self.state.fullmove_number += 1
        self.state.turn = self.state.turn.opponent

        # Record position for threefold-repetition detection.
        snapshot = self.state.position_snapshot(self.board.position_key())
        self._position_counts[snapshot] += 1
        _logger.debug(
            "Position snapshot recorded; count for current position: %d",
            self._position_counts[snapshot],
        )

    def _finalize_turn(self, move: Move) -> MoveOutcome:
        # NOTE (thesis baseline `thesis-baseline-2026-08-10`): checkmate and
        # stalemate detection (UC-5) are intentionally not implemented yet —
        # only the pre-existing 50-move draw rule can end a game here.
        opponent = move.piece.color.opponent
        gave_check = is_in_check(self.board, opponent)
        if self.state.halfmove_clock >= 100:
            _logger.debug("50-move rule triggered; declaring DRAW.")
            self._result = GameResult.DRAW
        elif max(self._position_counts.values(), default=0) >= 3:
            _logger.debug("Threefold repetition detected; declaring DRAW.")
            self._result = GameResult.DRAW
        return MoveOutcome(move=move, gave_check=gave_check, result=self._result)
