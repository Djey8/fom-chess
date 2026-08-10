import pytest

from chess.application.game import Game, GameResult
from chess.application.notation import format_move, parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import CastlingRights, GameState
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.presentation.console import _result_banner, ConsoleUI


def _play(game: Game, *moves: str) -> None:
    for move_text in moves:
        move = parse_move(move_text, game)
        game.make_move(move)


def _pos(square: str) -> Position:
    return Position.from_algebraic(square)


def test_f1_en_passant_target_expires_after_one_reply() -> None:
    game = Game()

    _play(game, "e4", "a6", "e5", "d5")
    en_passant_moves = {
        format_move(move) for move in game.legal_moves() if move.origin == _pos("e5")
    }
    assert "exd6" in en_passant_moves
    assert game.state.en_passant_target == _pos("d6")

    _play(game, "Nf3")
    assert game.state.en_passant_target is None


def test_f2_castling_rights_revoke_after_rook_capture_on_home_square() -> None:
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("a4"), Piece(PieceType.QUEEN, Color.BLACK))
    state = GameState(turn=Color.BLACK)
    game = Game(board=board, state=state)

    _play(game, "Qxa1")

    white_rights = game.state.white_castling
    assert white_rights.queenside is False
    assert white_rights.kingside is True


def test_f3_underpromotion_by_capture_uses_selected_piece_and_notation() -> None:
    board = Board.empty()
    board.set(_pos("g7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("h8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)

    move = parse_move("gxh8=N", game)
    outcome = game.make_move(move)

    promoted_piece = game.board.get(_pos("h8"))
    assert promoted_piece is not None
    assert promoted_piece.type is PieceType.KNIGHT
    assert format_move(outcome.move) == "gxh8=N"


def test_f4_stalemate_result_and_banner_text_match() -> None:
    game = Game()

    _play(game, "e3", "a5", "Qh5", "Ra6", "Qxa5", "h5", "h4", "Rah6", "Qxc7", "f6", "Qxd7", "Kf7", "Qxb7", "Qd3", "Qxb8", "Qh7", "Qxc8", "Kg6", "Qe6")

    assert game.result is GameResult.STALEMATE
    assert _result_banner(game.result) == "Stalemate — draw."


@pytest.mark.xfail(reason="Threefold repetition detection is not implemented yet.", strict=False)
def test_f5_threefold_repetition_declares_draw() -> None:
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("g1"), Piece(PieceType.KNIGHT, Color.WHITE))
    board.set(_pos("g8"), Piece(PieceType.KNIGHT, Color.BLACK))
    state = GameState(
        white_castling=CastlingRights(False, False),
        black_castling=CastlingRights(False, False),
    )
    game = Game(board=board, state=state)

    _play(game, "Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8")

    assert game.result is GameResult.DRAW
