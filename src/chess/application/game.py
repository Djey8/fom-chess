"""Game controller: orchestrates board, state, and rules."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..domain.board import Board
from ..domain.color import Color
from ..domain.game_state import GameState
from ..domain.move import Move, MoveKind
from ..domain.piece import PieceType
from ..domain.position import Position
from ..domain.rules import (
    apply_move,
    generate_legal_moves,
    is_in_check,
)


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
        self._logger = logging.getLogger(__name__)

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
        # Update castling rights BEFORE mutating board (we need piece info)
        self._update_castling_rights(move)
        # En-passant target tracking
        if move.kind is MoveKind.DOUBLE_PAWN:
            mid_row = (move.origin.row + move.target.row) // 2
            self.state.en_passant_target = Position(mid_row, move.origin.col)
            self._logger.debug(
                "En passant target set to %s after double pawn advance from %s",
                self.state.en_passant_target.algebraic,
                move.origin.algebraic,
            )
        else:
            if self.state.en_passant_target is not None:
                self._logger.debug(
                    "En passant target %s cleared (move %s->%s was not en passant capture)",
                    self.state.en_passant_target.algebraic,
                    move.origin.algebraic,
                    move.target.algebraic,
                )
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

    def _update_castling_rights(self, move: Move) -> None:
        piece = move.piece
        # King move loses both rights
        if piece.type is PieceType.KING:
            rights = self.state.castling_rights(piece.color)
            rights.kingside = False
            rights.queenside = False
        # Rook move loses the corresponding side
        if piece.type is PieceType.ROOK:
            row = 7 if piece.color is Color.WHITE else 0
            rights = self.state.castling_rights(piece.color)
            if move.origin == Position(row, 0):
                rights.queenside = False
            elif move.origin == Position(row, 7):
                rights.kingside = False
        # Rook captured on its home square removes opponent's right
        if move.is_capture and move.captured is not None and move.captured.type is PieceType.ROOK:
            opp_row = 7 if move.captured.color is Color.WHITE else 0
            if move.target == Position(opp_row, 0):
                self.state.castling_rights(move.captured.color).queenside = False
            elif move.target == Position(opp_row, 7):
                self.state.castling_rights(move.captured.color).kingside = False

    def _finalize_turn(self, move: Move) -> MoveOutcome:
        mover = move.piece.color
        opponent = mover.opponent
        gave_check = is_in_check(self.board, opponent)
        opp_moves = generate_legal_moves(self.board, opponent, self.state)
        if not opp_moves:
            if gave_check:
                self._result = (
                    GameResult.WHITE_WINS if mover is Color.WHITE else GameResult.BLACK_WINS
                )
            else:
                self._result = GameResult.STALEMATE
        elif self.state.halfmove_clock >= 100:
            self._result = GameResult.DRAW
        return MoveOutcome(move=move, gave_check=gave_check, result=self._result)
