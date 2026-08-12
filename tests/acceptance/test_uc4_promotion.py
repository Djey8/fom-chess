"""Fixed acceptance-test suite for UC-4 (pawn promotion incl. underpromotion).

See tests/acceptance/test_uc2_en_passant.py for the rationale: this suite is
part of the frozen thesis baseline `thesis-baseline-2026-08-10` and is not
written by whoever implements the ticket (manual or agent).

AC4 additionally requires UC-5 (checkmate detection) to be implemented, per
Epic UC-1's own dependency note.
"""

import pytest

from chess.application.game import Game, GameResult
from chess.application.notation import format_move, parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import GameState
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.domain.rules import generate_pseudo_legal_moves_for


def _pos(square: str) -> Position:
    return Position.from_algebraic(square)


_PROMOTION_TYPES = {PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT}


# ---------------------------------------------------------------------------
# AC1 -- four distinct promotion moves per target square (advance / capture)
# ---------------------------------------------------------------------------
def test_ac1_promotion_by_advance_generates_four_choices():
    board = Board.empty()
    board.set(_pos("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("e7"), GameState())
    promos = [m for m in moves if m.target.algebraic == "e8" and m.is_promotion]
    assert len(promos) == 4
    assert {m.promotion for m in promos} == _PROMOTION_TYPES


def test_ac1_promotion_by_capture_generates_four_choices():
    board = Board.empty()
    board.set(_pos("g7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("h8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("g7"), GameState())
    promos = [m for m in moves if m.target.algebraic == "h8" and m.is_promotion]
    assert len(promos) == 4
    assert {m.promotion for m in promos} == _PROMOTION_TYPES


# ---------------------------------------------------------------------------
# AC2 -- executing a promotion replaces the pawn and formats correctly
# ---------------------------------------------------------------------------
def test_ac2_promotion_by_advance_replaces_pawn_and_formats_notation():
    board = Board.empty()
    board.set(_pos("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)
    move = parse_move("e7e8q", game)
    outcome = game.make_move(move)
    promoted = game.board.get(_pos("e8"))
    assert promoted is not None
    assert promoted.type is PieceType.QUEEN
    assert promoted.color is Color.WHITE
    assert format_move(outcome.move) == "e8=Q"


def test_ac2_underpromotion_by_capture_replaces_pawn_and_formats_notation():
    board = Board.empty()
    board.set(_pos("g7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("h8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)
    move = parse_move("gxh8=N", game)
    outcome = game.make_move(move)
    promoted = game.board.get(_pos("h8"))
    assert promoted is not None
    assert promoted.type is PieceType.KNIGHT
    assert format_move(outcome.move) == "gxh8=N"


# ---------------------------------------------------------------------------
# AC3 -- promotion is mandatory; remaining a pawn on the last rank is illegal
# ---------------------------------------------------------------------------
def test_ac3_pawn_reaching_last_rank_cannot_remain_a_pawn():
    board = Board.empty()
    board.set(_pos("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("e7"), GameState())
    to_last_rank = [m for m in moves if m.target.algebraic == "e8"]
    assert to_last_rank
    assert all(m.is_promotion for m in to_last_rank)


# ---------------------------------------------------------------------------
# AC4 -- a promotion delivering checkmate is detected via the promoted piece
# (requires UC-5 checkmate detection)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    reason="AC4 requires UC-5 (checkmate detection) which is not yet implemented.",
    strict=False,
)
def test_ac4_promotion_delivering_checkmate_is_detected_with_promoted_piece():
    board = Board.empty()
    board.set(_pos("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("b7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("h8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("g7"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("h7"), Piece(PieceType.PAWN, Color.BLACK))
    game = Game(board=board)
    # b7-b8=Q delivers back-rank mate: the black king cannot reach g7/h7
    # (own pawns) and g8/h8 are both covered along the 8th rank.
    move = parse_move("b7b8q", game)
    game.make_move(move)
    assert game.result is GameResult.WHITE_WINS
