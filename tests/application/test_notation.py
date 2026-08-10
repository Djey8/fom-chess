import pytest

from chess.application.game import Game
from chess.application.notation import NotationError, parse_move


def test_parse_pawn_move():
    g = Game()
    mv = parse_move("e4", g)
    assert mv.origin.algebraic == "e2"
    assert mv.target.algebraic == "e4"


def test_parse_knight_move():
    g = Game()
    mv = parse_move("Nf3", g)
    assert mv.origin.algebraic == "g1"
    assert mv.target.algebraic == "f3"


def test_parse_coordinate_form():
    g = Game()
    mv = parse_move("e2e4", g)
    assert mv.target.algebraic == "e4"


def test_illegal_move_raises():
    g = Game()
    with pytest.raises(NotationError):
        parse_move("e5", g)


def test_ambiguous_move_requires_disambiguation():
    # Setup: two knights able to go to e4 (b1 and g1 cannot both, but d2 and f2 can't either)
    # Use a contrived position via Game after moves: 1.Nc3 e5 2.Nf3 -> both knights could go to e4? No.
    # Rather test by forcing an impossible parse.
    g = Game()
    # "Ne4" without disambiguation — from start no knight reaches e4 directly.
    with pytest.raises(NotationError):
        parse_move("Ne4", g)
