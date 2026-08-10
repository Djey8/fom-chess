from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.piece import PieceType
from chess.domain.position import Position


def test_standard_starting_position():
    b = Board.standard()
    # White back rank
    assert b.get(Position.from_algebraic("a1")).type is PieceType.ROOK
    assert b.get(Position.from_algebraic("e1")).type is PieceType.KING
    assert b.get(Position.from_algebraic("d1")).type is PieceType.QUEEN
    # Pawns
    for file in "abcdefgh":
        assert b.get(Position.from_algebraic(f"{file}2")).color is Color.WHITE
        assert b.get(Position.from_algebraic(f"{file}7")).color is Color.BLACK
    # Empty middle
    assert b.is_empty(Position.from_algebraic("e4"))


def test_find_king():
    b = Board.standard()
    assert b.find_king(Color.WHITE) == Position.from_algebraic("e1")
    assert b.find_king(Color.BLACK) == Position.from_algebraic("e8")


def test_clone_independence():
    b = Board.standard()
    c = b.clone()
    c.set(Position.from_algebraic("e2"), None)
    assert b.get(Position.from_algebraic("e2")) is not None
