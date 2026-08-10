import pytest

from chess.application.game import Game, GameResult, IllegalMoveError
from chess.application.notation import parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import GameState
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position


def play(game: Game, *sans: str) -> None:
    for san in sans:
        move = parse_move(san, game)
        game.make_move(move)


def test_new_game_white_to_move():
    game = Game()
    assert game.turn is Color.WHITE


def test_alternating_turns():
    game = Game()
    play(game, "e4")
    assert game.turn is Color.BLACK
    play(game, "e5")
    assert game.turn is Color.WHITE


def test_black_cannot_move_on_whites_turn():
    game = Game()
    with pytest.raises(Exception):
        # e7e5 is black's move, white to move now -> should fail to parse as legal.
        play(game, "e7e5")


def test_illegal_move_rejected():
    game = Game()
    with pytest.raises(Exception):
        play(game, "e5")  # pawn cannot jump to e5 on the first move


def test_scholars_mate_is_checkmate():
    game = Game()
    play(game, "e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7")
    assert game.result is GameResult.WHITE_WINS


def test_fools_mate_is_checkmate():
    game = Game()
    play(game, "f3", "e5", "g4", "Qh4")
    assert game.result is GameResult.BLACK_WINS


def test_castling_kingside():
    game = Game()
    play(game, "e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "O-O")
    # White king on g1, rook on f1
    from chess.domain.position import Position
    from chess.domain.piece import PieceType

    assert game.board.get(Position.from_algebraic("g1")).type is PieceType.KING
    assert game.board.get(Position.from_algebraic("f1")).type is PieceType.ROOK


def test_en_passant_capture():
    game = Game()
    # 1.e4 a6 2.e5 d5 3.exd6 (en passant)
    play(game, "e4", "a6", "e5", "d5", "exd6")
    from chess.domain.position import Position

    # d5 pawn captured, white pawn now on d6, d5 is empty
    assert game.board.is_empty(Position.from_algebraic("d5"))
    assert game.board.get(Position.from_algebraic("d6")) is not None


def test_promotion_to_queen_via_coordinate():
    game = Game()
    # Set up a direct promotion: clear the path manually by playing a contrived sequence
    # is tedious. Use Board/state directly.
    from chess.domain.board import Board
    from chess.domain.piece import Piece, PieceType
    from chess.domain.position import Position

    board = Board.empty()
    board.set(Position.from_algebraic("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("a8"), Piece(PieceType.KING, Color.BLACK))
    g = Game(board=board)
    move = parse_move("e7e8q", g)
    g.make_move(move)
    promoted = g.board.get(Position.from_algebraic("e8"))
    assert promoted.type is PieceType.QUEEN
    assert promoted.color is Color.WHITE


def test_cannot_leave_king_in_check():
    # White king on e1, white rook on e2, black rook on e8. Rook is pinned.
    from chess.domain.board import Board
    from chess.domain.piece import Piece, PieceType
    from chess.domain.position import Position

    board = Board.empty()
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("e2"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(Position.from_algebraic("e8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(Position.from_algebraic("a8"), Piece(PieceType.KING, Color.BLACK))
    g = Game(board=board)
    # Moving the pinned rook off the e-file is illegal and must be rejected
    # (either by the parser or the controller).
    with pytest.raises(Exception):
        move = parse_move("Ra2", g)
        g.make_move(move)

    # And the rook's legal moves must stay on the e-file.
    from chess.domain.position import Position

    rook_moves = g.legal_moves_from(Position.from_algebraic("e2"))
    assert all(m.target.file == "e" for m in rook_moves)


# ---------------------------------------------------------------------------
# 50-move draw rule
# ---------------------------------------------------------------------------

def _minimal_board() -> tuple[Board, GameState]:
    """Return a board with only the two kings so we can drive the halfmove clock
    by shuttling the kings back and forth without any pawn move or capture."""
    board = Board.empty()
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("e8"), Piece(PieceType.KING, Color.BLACK))
    return board, GameState()


def test_halfmove_clock_increments_on_king_move():
    board, state = _minimal_board()
    g = Game(board=board, state=state)
    assert g.state.halfmove_clock == 0
    play(g, "Kd1")  # white king moves
    assert g.state.halfmove_clock == 1
    play(g, "Kd8")  # black king moves
    assert g.state.halfmove_clock == 2


def test_halfmove_clock_resets_on_pawn_move():
    g = Game()
    play(g, "e4")   # pawn move — clock must reset to 0
    assert g.state.halfmove_clock == 0
    play(g, "Nc6")  # knight move — clock increments
    assert g.state.halfmove_clock == 1
    play(g, "Nf3")  # another non-pawn/non-capture move
    assert g.state.halfmove_clock == 2
    play(g, "d5")   # black pawn move — clock resets again
    assert g.state.halfmove_clock == 0


def test_halfmove_clock_resets_on_capture():
    g = Game()
    # Advance white e-pawn then black d-pawn so white can capture.
    play(g, "e4", "d5", "Nf3")   # clock is 1 after Nf3
    assert g.state.halfmove_clock == 1
    play(g, "Nc6", "exd5")       # exd5 is a capture — clock resets
    assert g.state.halfmove_clock == 0


def test_50_move_rule_triggers_draw():
    """Driving the halfmove clock to 100 (50 full moves) without a pawn move
    or capture must produce GameResult.DRAW."""
    board, state = _minimal_board()
    # Pre-load the clock to 98 so the next (99th) half-move brings it to 99,
    # and the one after (100th) triggers the draw.
    state.halfmove_clock = 98
    g = Game(board=board, state=state)
    assert g.result is GameResult.ONGOING

    # Half-move 99: white king moves — clock → 99, game still ongoing.
    play(g, "Kd1")
    assert g.state.halfmove_clock == 99
    assert g.result is GameResult.ONGOING

    # Half-move 100: black king moves — clock → 100, game is DRAW.
    play(g, "Kd8")
    assert g.state.halfmove_clock == 100
    assert g.result is GameResult.DRAW


def test_50_move_draw_cannot_play_after():
    """Once the draw is triggered the game must be over."""
    board, state = _minimal_board()
    state.halfmove_clock = 99
    g = Game(board=board, state=state)
    play(g, "Kd1")  # brings clock to 100, triggers DRAW
    assert g.is_over()
    with pytest.raises(IllegalMoveError):
        play(g, "Kd8")  # must be rejected because game is over


def test_checkmate_takes_priority_over_50_move_rule():
    """If a checkmate happens on the same move that would trigger the 50-move
    draw, checkmate must win."""
    # Position: white king a1, white rook b1, white queen b2, black king a8.
    # Qb2-b8# delivers checkmate (rook on b1 protects the queen; queen on b8
    # covers a7 diagonally so the black king has no escape).  The move is not
    # a capture, so the halfmove clock would reach 100 — but checkmate wins.
    board = Board.empty()
    board.set(Position.from_algebraic("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("b1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(Position.from_algebraic("b2"), Piece(PieceType.QUEEN, Color.WHITE))
    board.set(Position.from_algebraic("a8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(halfmove_clock=99)
    g = Game(board=board, state=state)
    # Qb2-b8#: clock goes 99→100, but checkmate takes priority over DRAW
    play(g, "Qb8")
    assert g.result is GameResult.WHITE_WINS


# ---------------------------------------------------------------------------
# En passant (UC-2)
# ---------------------------------------------------------------------------
def test_en_passant_target_set_after_double_pawn_advance():
    """AC-4: game state records the en passant target square after a double pawn advance."""
    g = Game()
    play(g, "e4")
    # After e2e4 (double pawn advance), target must be e3
    assert g.state.en_passant_target == Position.from_algebraic("e3")


def test_en_passant_target_cleared_after_next_move():
    """AC-3/4: the en passant target is cleared when the opponent does not capture en passant."""
    g = Game()
    play(g, "e4", "d5")
    # Black played d5 (double pawn) so target should now be d6
    assert g.state.en_passant_target == Position.from_algebraic("d6")
    # White plays a non-capturing move; target is cleared
    play(g, "Nf3")
    assert g.state.en_passant_target is None


def test_en_passant_capture_executes_correctly():
    """AC-1/2: en passant capture removes the captured pawn from its actual square."""
    g = Game()
    # 1.e4 e5 2.e5 — white pawn on e5; 2...d5 — black pawn double-advance, target d6
    play(g, "e4", "e5", "Nf3", "d5")
    # Move white pawn to e5 first; set up board directly for clarity
    # Simpler: start from scratch with a custom board
    board = Board.empty()
    board.set(Position.from_algebraic("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(Position.from_algebraic("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE, en_passant_target=Position.from_algebraic("d6"))
    g2 = Game(board=board, state=state)

    # White pawn e5xd6 en passant
    move = g2.find_legal_move(
        Position.from_algebraic("e5"), Position.from_algebraic("d6")
    )
    assert move is not None
    g2.make_move(move)

    # Captured black pawn must be gone from d5
    assert g2.board.get(Position.from_algebraic("d5")) is None
    # White pawn is on d6
    wp = g2.board.get(Position.from_algebraic("d6"))
    assert wp is not None
    assert wp.color is Color.WHITE
    # En passant target must be cleared
    assert g2.state.en_passant_target is None


def test_en_passant_expires_after_one_move():
    """AC-3: the en passant option is no longer available after one full move passes."""
    board = Board.empty()
    board.set(Position.from_algebraic("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(Position.from_algebraic("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE, en_passant_target=Position.from_algebraic("d6"))
    g = Game(board=board, state=state)

    # White plays a different move (king step), not en passant
    move = g.find_legal_move(
        Position.from_algebraic("e1"), Position.from_algebraic("d1")
    )
    assert move is not None
    g.make_move(move)

    # After white's move, en passant target is cleared
    assert g.state.en_passant_target is None
    # Black's legal moves must not include en passant
    legal = g.legal_moves(Color.BLACK)
    assert all(m.kind.value != "en_passant" for m in legal)
