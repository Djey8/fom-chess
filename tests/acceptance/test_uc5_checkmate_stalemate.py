"""Fixed acceptance-test suite for UC-5 (detect checkmate and stalemate).

See tests/acceptance/test_uc2_en_passant.py for the rationale: this suite is
part of the frozen thesis baseline `thesis-baseline-2026-08-10` and is not
written by whoever implements the ticket (manual or agent).

Most tests are expected to fail until UC-5 is implemented. AC4 is a
regression guard for behavior the baseline already provides (see the
un-marked test below) -- it is not owned by UC-5.
"""

import pytest

from chess.application.game import Game, GameResult, IllegalMoveError
from chess.application.notation import parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import GameState
from chess.domain.move import Move, MoveKind
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.domain.rules import generate_legal_moves
from chess.presentation.console import ConsoleUI

_STALEMATE_SEQUENCE = (
    "e3", "a5", "Qh5", "Ra6", "Qxa5", "h5", "h4", "Rah6",
    "Qxc7", "f6", "Qxd7", "Kf7", "Qxb7", "Qd3", "Qxb8", "Qh7",
    "Qxc8", "Kg6", "Qe6",
)


def _pos(square: str) -> Position:
    return Position.from_algebraic(square)


def _play(game: Game, *moves: str) -> None:
    for move_text in moves:
        move = parse_move(move_text, game)
        game.make_move(move)


def _bogus_move_for_any_piece(game: Game) -> Move:
    """A structurally valid Move for whatever piece happens to be on the
    board -- only used to probe the ``is_over()`` guard in ``make_move``,
    not to represent a real legal move."""
    piece_pos, piece = next(game.board.iter_pieces())
    return Move(piece, piece_pos, piece_pos, MoveKind.NORMAL)


_XFAIL = pytest.mark.xfail(
    reason="Checkmate/stalemate result detection (UC-5) is not implemented yet (thesis baseline).",
    strict=False,
)


# ---------------------------------------------------------------------------
# AC1 -- checkmate ends the game with the correct winner, no further moves
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac1_checkmate_detected_as_white_wins():
    game = Game()
    _play(game, "e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7")
    assert game.result is GameResult.WHITE_WINS


@_XFAIL
def test_ac1_checkmate_detected_as_black_wins():
    game = Game()
    _play(game, "f3", "e5", "g4", "Qh4")
    assert game.result is GameResult.BLACK_WINS


@_XFAIL
def test_ac1_no_further_moves_accepted_after_checkmate():
    game = Game()
    _play(game, "f3", "e5", "g4", "Qh4")
    assert game.is_over()
    with pytest.raises(IllegalMoveError):
        game.make_move(_bogus_move_for_any_piece(game))


# ---------------------------------------------------------------------------
# AC2 -- stalemate ends the game as a draw, no further moves
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac2_stalemate_declared_as_draw():
    game = Game()
    _play(game, *_STALEMATE_SEQUENCE)
    assert game.result is GameResult.STALEMATE


@_XFAIL
def test_ac2_no_further_moves_accepted_after_stalemate():
    game = Game()
    _play(game, *_STALEMATE_SEQUENCE)
    assert game.is_over()
    with pytest.raises(IllegalMoveError):
        game.make_move(_bogus_move_for_any_piece(game))


# ---------------------------------------------------------------------------
# AC3 -- the UI displays a checkmate/stalemate message when the game ends
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac3_ui_displays_checkmate_banner():
    moves = iter(["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7", "quit"])
    outputs: list[str] = []
    ui = ConsoleUI(input_fn=lambda _: next(moves), output_fn=outputs.append, colored=False)
    ui.run()
    assert "Checkmate" in "\n".join(outputs)


@_XFAIL
def test_ac3_ui_displays_stalemate_banner():
    moves = iter(list(_STALEMATE_SEQUENCE) + ["quit"])
    outputs: list[str] = []
    ui = ConsoleUI(input_fn=lambda _: next(moves), output_fn=outputs.append, colored=False)
    ui.run()
    assert "Stalemate" in "\n".join(outputs)


# ---------------------------------------------------------------------------
# AC4 -- legal-move generation must keep excluding check-exposing moves,
# including pinned pieces. Already true at baseline (owned by the generic
# check-safety filter, not by UC-5) -- kept unmarked as a regression guard.
# ---------------------------------------------------------------------------
def test_ac4_legal_moves_already_exclude_pinned_piece_check_exposure():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e2"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    legal = generate_legal_moves(board, Color.WHITE, state)
    rook_moves = [m for m in legal if m.origin == _pos("e2")]
    assert rook_moves
    for m in rook_moves:
        assert m.target.file == "e"
