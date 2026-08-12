"""Tests for UC-5: checkmate and stalemate detection.

Covers:
- Three known checkmate positions (AC-1)
- Two known stalemate positions (AC-2)
- One near-stalemate position where a legal move still exists (AC-5)
"""

import pytest

from chess.application.game import Game, GameResult, IllegalMoveError
from chess.application.notation import parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import GameState
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position


def _pos(algebraic: str) -> Position:
    return Position.from_algebraic(algebraic)


def _piece(pt: PieceType, color: Color) -> Piece:
    return Piece(pt, color)


def _game(board: Board, turn: Color = Color.WHITE) -> Game:
    state = GameState(turn=turn)
    return Game(board=board, state=state)


# ---------------------------------------------------------------------------
# Checkmate positions
# ---------------------------------------------------------------------------

def test_checkmate_scholars_mate():
    """Scholar's mate: White delivers checkmate after 1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6 4.Qxf7#."""
    game = Game()
    for san in ("e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7"):
        move = parse_move(san, game)
        game.make_move(move)
    assert game.result is GameResult.WHITE_WINS
    assert game.is_over()


def test_checkmate_back_rank():
    """Back-rank checkmate: White rook delivers checkmate on rank 8."""
    board = Board.empty()
    # Black king trapped on h8 with pawns blocking escape
    board.set(_pos("h8"), _piece(PieceType.KING, Color.BLACK))
    board.set(_pos("g7"), _piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("h7"), _piece(PieceType.PAWN, Color.BLACK))
    # White pieces
    board.set(_pos("e1"), _piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), _piece(PieceType.ROOK, Color.WHITE))

    # It is Black's turn but Black is already in checkmate
    state = GameState(turn=Color.BLACK)
    game = Game(board=board, state=state)

    # generate_legal_moves for black should be empty and is_in_check is True
    from chess.domain.rules import generate_legal_moves, is_in_check
    assert is_in_check(board, Color.BLACK)
    assert generate_legal_moves(board, Color.BLACK, state) == []

    # Drive this through the game by making the last white move
    board2 = Board.empty()
    board2.set(_pos("h8"), _piece(PieceType.KING, Color.BLACK))
    board2.set(_pos("g7"), _piece(PieceType.PAWN, Color.BLACK))
    board2.set(_pos("h7"), _piece(PieceType.PAWN, Color.BLACK))
    board2.set(_pos("e1"), _piece(PieceType.KING, Color.WHITE))
    board2.set(_pos("a1"), _piece(PieceType.ROOK, Color.WHITE))  # rook not yet on a8

    game2 = _game(board2, Color.WHITE)
    move = parse_move("Ra8", game2)
    outcome = game2.make_move(move)
    assert outcome.result is GameResult.WHITE_WINS
    assert game2.is_over()


def test_checkmate_two_rooks():
    """Fool's mate: Black delivers checkmate in 2 moves."""
    game = Game()
    for san in ("f3", "e5", "g4", "Qh4"):
        move = parse_move(san, game)
        game.make_move(move)
    assert game.result is GameResult.BLACK_WINS
    assert game.is_over()


# ---------------------------------------------------------------------------
# Stalemate positions
# ---------------------------------------------------------------------------

def test_stalemate_lone_king():
    """Classic stalemate: Black king on a1, no legal moves, not in check."""
    board = Board.empty()
    board.set(_pos("a1"), _piece(PieceType.KING, Color.BLACK))
    board.set(_pos("c2"), _piece(PieceType.KING, Color.WHITE))
    board.set(_pos("b3"), _piece(PieceType.QUEEN, Color.WHITE))  # controls b2, a2

    # White queen to a3 delivers stalemate (controls b2 as well, king stuck on a1)
    # Arrange queen so the final move creates stalemate
    board2 = Board.empty()
    board2.set(_pos("a1"), _piece(PieceType.KING, Color.BLACK))
    board2.set(_pos("c2"), _piece(PieceType.KING, Color.WHITE))
    board2.set(_pos("c3"), _piece(PieceType.QUEEN, Color.WHITE))

    game = _game(board2, Color.WHITE)
    move = parse_move("Qb3", game)
    outcome = game.make_move(move)
    assert outcome.result is GameResult.STALEMATE
    assert game.is_over()


def test_stalemate_corner():
    """Stalemate with Black king in corner, White queen one step away."""
    board = Board.empty()
    board.set(_pos("h8"), _piece(PieceType.KING, Color.BLACK))
    board.set(_pos("a1"), _piece(PieceType.KING, Color.WHITE))
    board.set(_pos("f7"), _piece(PieceType.QUEEN, Color.WHITE))

    game = _game(board, Color.WHITE)
    # Qg6 puts queen on g6 — king on h8 has no legal moves and is NOT in check
    move = parse_move("Qg6", game)
    outcome = game.make_move(move)
    assert outcome.result is GameResult.STALEMATE
    assert game.is_over()


# ---------------------------------------------------------------------------
# Near-stalemate: one legal move still exists
# ---------------------------------------------------------------------------

def test_near_stalemate_has_legal_move():
    """Position that looks like stalemate but Black has one legal pawn move."""
    board = Board.empty()
    board.set(_pos("a1"), _piece(PieceType.KING, Color.BLACK))
    board.set(_pos("c2"), _piece(PieceType.KING, Color.WHITE))
    board.set(_pos("c3"), _piece(PieceType.QUEEN, Color.WHITE))
    # Extra black pawn on b6 gives Black a legal move
    board.set(_pos("b6"), _piece(PieceType.PAWN, Color.BLACK))

    game = _game(board, Color.WHITE)
    move = parse_move("Qb3", game)
    outcome = game.make_move(move)
    # Game must still be ONGOING because Black can play b5
    assert outcome.result is GameResult.ONGOING
    assert not game.is_over()


# ---------------------------------------------------------------------------
# Post-game rejection
# ---------------------------------------------------------------------------

def test_no_moves_accepted_after_checkmate():
    """After checkmate, any further move attempt raises IllegalMoveError."""
    game = Game()
    for san in ("e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7"):
        move = parse_move(san, game)
        game.make_move(move)
    assert game.is_over()
    with pytest.raises(IllegalMoveError):
        # Game is already over; make_move must raise IllegalMoveError.
        from chess.domain.move import Move, MoveKind
        from chess.domain.piece import Piece

        dummy_board = game.board
        dummy_piece = dummy_board.get(_pos("d7"))
        dummy_move = Move(
            piece=dummy_piece,
            origin=_pos("d7"),
            target=_pos("d5"),
            kind=MoveKind.DOUBLE_PAWN,
        )
        game.make_move(dummy_move)
