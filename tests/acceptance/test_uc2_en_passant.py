"""Fixed acceptance-test suite for UC-2 (implement en passant capture).

Maps 1:1 onto the numbered acceptance criteria in the Jira Ticket Pack
(Atlas: Projekte/FOM Chess/Thesis-Studie/Jira Ticket Pack.md, UC-2). Written
and committed as part of the frozen thesis baseline
`thesis-baseline-2026-08-10` so the manual run and every agent run are
graded against the identical, externally-fixed test suite (see Kap. 2,
"Testabdeckung (TF1)" in the thesis) instead of each writing (and grading
against) their own tests.

All tests are expected to fail until UC-2 is implemented.
"""

import pytest

from chess.application.game import Game
from chess.application.notation import format_move, parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import GameState
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.domain.rules import generate_pseudo_legal_moves_for


def _pos(square: str) -> Position:
    return Position.from_algebraic(square)


def _play(game: Game, *moves: str) -> None:
    for move_text in moves:
        move = parse_move(move_text, game)
        game.make_move(move)


_XFAIL = pytest.mark.xfail(
    reason="En passant capture (UC-2) is not implemented yet (thesis baseline).",
    strict=False,
)


@_XFAIL
def test_ac1_en_passant_capture_included_in_legal_moves():
    """AC1: opponent pawn double-advances beside my pawn -> capture is legal."""
    board = Board.empty()
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(en_passant_target=_pos("d6"))
    moves = generate_pseudo_legal_moves_for(board, _pos("e5"), state)
    assert any(m.target.algebraic == "d6" and m.captured is not None for m in moves)


@_XFAIL
def test_ac2_en_passant_removes_captured_pawn_from_its_actual_square():
    """AC2: the captured pawn disappears from its own square, not the target."""
    game = Game()
    _play(game, "e4", "a6", "e5", "d5", "exd6")
    assert game.board.is_empty(_pos("d5"))
    captured_replacement = game.board.get(_pos("d6"))
    assert captured_replacement is not None
    assert captured_replacement.type is PieceType.PAWN
    assert captured_replacement.color is Color.WHITE


@_XFAIL
def test_ac3_en_passant_right_expires_after_one_full_move():
    """AC3: once White plays anything other than the capture, it disappears
    from the legal move list (the right exists only on the immediate reply)."""
    game = Game()
    _play(game, "e4", "a6", "e5", "d5")
    assert any(format_move(m) == "exd6" for m in game.legal_moves())

    _play(game, "Nf3")
    assert game.state.en_passant_target is None


@_XFAIL
def test_ac4_two_square_advance_sets_en_passant_target():
    """AC4 (part 1): any two-square pawn advance sets the target square."""
    game = Game()
    _play(game, "e4")
    assert game.state.en_passant_target == _pos("e3")


@_XFAIL
def test_ac4_en_passant_target_cleared_after_unrelated_move():
    """AC4 (part 2): the target clears again after the next move if unused."""
    game = Game()
    _play(game, "e4", "a6")
    assert game.state.en_passant_target is None
