"""En passant rule-generation tests."""

from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import GameState
from chess.domain.move import MoveKind
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.domain.rules import generate_legal_moves


def _pos(square: str) -> Position:
    """Return a board position from algebraic notation."""
    return Position.from_algebraic(square)


def test_en_passant_in_legal_move_list() -> None:
    """Legal move generation includes en passant when the target is valid."""
    board = Board.empty()
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE, en_passant_target=_pos("d6"))

    legal_moves = generate_legal_moves(board, Color.WHITE, state)

    assert any(
        move.origin == _pos("e5")
        and move.target == _pos("d6")
        and move.kind is MoveKind.EN_PASSANT
        for move in legal_moves
    )
