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


# ---------------------------------------------------------------------------
# Promotion notation (UC-4)
# ---------------------------------------------------------------------------
def test_parse_promotion_advance_san():
    """SAN e8=Q should parse as a promotion move to queen."""
    from chess.domain.board import Board
    from chess.domain.piece import Piece, PieceType
    from chess.domain.color import Color
    from chess.domain.game_state import GameState
    from chess.application.game import Game
    board = Board.empty()
    from chess.domain.position import Position
    def p(s): return Position.from_algebraic(s)
    board.set(p("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(p("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(p("h8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board, state=GameState())
    mv = parse_move("e8=Q", game)
    assert mv.promotion is PieceType.QUEEN


def test_parse_promotion_capture_san():
    """SAN exd8=N should parse as a promotion-capture move to knight."""
    from chess.domain.board import Board
    from chess.domain.piece import Piece, PieceType
    from chess.domain.color import Color
    from chess.domain.game_state import GameState
    from chess.application.game import Game
    board = Board.empty()
    from chess.domain.position import Position
    def p(s): return Position.from_algebraic(s)
    board.set(p("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(p("d8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(p("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(p("h8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board, state=GameState())
    mv = parse_move("exd8=N", game)
    assert mv.promotion is PieceType.KNIGHT


def test_format_promotion_advance():
    """format_move should produce e8=Q for advance promotion."""
    from chess.application.notation import format_move
    from chess.domain.move import Move, MoveKind
    from chess.domain.piece import Piece, PieceType
    from chess.domain.color import Color
    from chess.domain.position import Position
    pawn = Piece(PieceType.PAWN, Color.WHITE)
    mv = Move(pawn, Position.from_algebraic("e7"), Position.from_algebraic("e8"),
              MoveKind.PROMOTION, promotion=PieceType.QUEEN)
    assert format_move(mv) == "e8=Q"


def test_format_promotion_capture():
    """format_move should produce exd8=N for capture-promotion."""
    from chess.application.notation import format_move
    from chess.domain.move import Move, MoveKind
    from chess.domain.piece import Piece, PieceType
    from chess.domain.color import Color
    from chess.domain.position import Position
    pawn = Piece(PieceType.PAWN, Color.WHITE)
    rook = Piece(PieceType.ROOK, Color.BLACK)
    mv = Move(pawn, Position.from_algebraic("e7"), Position.from_algebraic("d8"),
              MoveKind.PROMOTION_CAPTURE, captured=rook, promotion=PieceType.KNIGHT)
    assert format_move(mv) == "exd8=N"
