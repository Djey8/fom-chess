"""Fixed acceptance-test suite for UC-3 (implement full castling legality checks).

See tests/acceptance/test_uc2_en_passant.py for the rationale: this suite is
part of the frozen thesis baseline `thesis-baseline-2026-08-10` and is not
written by whoever implements the ticket (manual or agent).

All tests are expected to fail until UC-3 is implemented.
"""

import pytest

from chess.application.game import Game
from chess.application.notation import parse_move
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
    reason="Castling legality (UC-3) is not implemented yet (thesis baseline).",
    strict=False,
)


# ---------------------------------------------------------------------------
# AC1 -- all four castle types available when conditions hold
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac1_white_kingside_castling_available():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert any(m.target.algebraic == "g1" for m in moves)


@_XFAIL
def test_ac1_white_queenside_castling_available():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert any(m.target.algebraic == "c1" for m in moves)


@_XFAIL
def test_ac1_black_kingside_castling_available():
    board = Board.empty()
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("h8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    state = GameState(turn=Color.BLACK)
    moves = generate_pseudo_legal_moves_for(board, _pos("e8"), state)
    assert any(m.target.algebraic == "g8" for m in moves)


@_XFAIL
def test_ac1_black_queenside_castling_available():
    board = Board.empty()
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("a8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    state = GameState(turn=Color.BLACK)
    moves = generate_pseudo_legal_moves_for(board, _pos("e8"), state)
    assert any(m.target.algebraic == "c8" for m in moves)


# ---------------------------------------------------------------------------
# AC2 -- check / passes-through-attacked / lands-on-attacked block castling
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac2_castling_blocked_when_king_in_check():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert all(m.target.algebraic != "g1" for m in moves)


@_XFAIL
def test_ac2_castling_blocked_when_king_passes_through_attacked_square():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("f8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert all(m.target.algebraic != "g1" for m in moves)


@_XFAIL
def test_ac2_castling_blocked_when_king_lands_on_attacked_square():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("g8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert all(m.target.algebraic != "g1" for m in moves)


# ---------------------------------------------------------------------------
# AC3 -- squares between king and rook must be empty
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac3_castling_blocked_when_square_between_king_and_rook_occupied():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("f1"), Piece(PieceType.BISHOP, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert all(m.target.algebraic != "g1" for m in moves)


# ---------------------------------------------------------------------------
# AC4 -- rights permanently revoked by king move, rook move, rook capture
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac4_rights_revoked_after_king_move():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("a1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)
    _play(game, "e1d1")
    assert game.state.white_castling.kingside is False
    assert game.state.white_castling.queenside is False


@_XFAIL
def test_ac4_rights_revoked_after_rook_moves_from_home_square():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)
    _play(game, "h1g1")
    assert game.state.white_castling.kingside is False


@_XFAIL
def test_ac4_rights_revoked_after_rook_captured_on_home_square():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("a4"), Piece(PieceType.QUEEN, Color.BLACK))
    state = GameState(turn=Color.BLACK)
    game = Game(board=board, state=state)
    _play(game, "Qxa1")
    assert game.state.white_castling.queenside is False
    assert game.state.white_castling.kingside is True


# ---------------------------------------------------------------------------
# AC5 -- castling execution places king and rook correctly, as one move
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac5_kingside_castling_places_king_and_rook_correctly():
    game = Game()
    _play(game, "e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "O-O")
    assert game.board.get(_pos("g1")).type is PieceType.KING
    assert game.board.get(_pos("f1")).type is PieceType.ROOK
    assert game.board.is_empty(_pos("e1"))
    assert game.board.is_empty(_pos("h1"))


@_XFAIL
def test_ac5_queenside_castling_places_king_and_rook_correctly():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)
    _play(game, "O-O-O")
    assert game.board.get(_pos("c1")).type is PieceType.KING
    assert game.board.get(_pos("d1")).type is PieceType.ROOK
    assert game.board.is_empty(_pos("e1"))
    assert game.board.is_empty(_pos("a1"))
