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




# ---------------------------------------------------------------------------
# UC-6: Threefold repetition draw
# ---------------------------------------------------------------------------

def _two_kings_board() -> tuple[Board, GameState]:
    """Board with only two kings for clean repetition testing."""
    board = Board.empty()
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState()
    # Disable all castling rights so the snapshot is stable.
    state.white_castling.kingside = False
    state.white_castling.queenside = False
    state.black_castling.kingside = False
    state.black_castling.queenside = False
    return board, state


def test_threefold_repetition_basic():
    """Shuttling kings back to the same squares three times triggers DRAW."""
    board, state = _two_kings_board()
    g = Game(board=board, state=state)
    assert g.result is GameResult.ONGOING

    # Occurrence 1 of e1/e8 position is the starting position (tracked
    # only after moves, so we just need the position to appear 3 times *after*
    # moves have been applied).  Shuttle: e1->d1->e1 for white, e8->d8->e8 for black.
    play(g, "Kd1", "Kd8", "Ke1", "Ke8")   # back to start — 2nd occurrence
    assert g.result is GameResult.ONGOING
    play(g, "Kd1", "Kd8", "Ke1", "Ke8")   # back to start — 3rd occurrence
    assert g.result is GameResult.DRAW


def test_threefold_repetition_non_consecutive():
    """Repetition need not be consecutive; draw fires on the third occurrence."""
    # Start from d1/d8 so the starting position (A) is not the same as e1/e8.
    board = Board.empty()
    board.set(Position.from_algebraic("d1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("d8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState()
    state.white_castling.kingside = False
    state.white_castling.queenside = False
    state.black_castling.kingside = False
    state.black_castling.queenside = False
    g = Game(board=board, state=state)

    # A = d1/d8 (white to move) — 1st occurrence recorded at Game init.
    play(g, "Kc1", "Kc8")   # B — intermediate position
    play(g, "Kd1", "Kd8")   # A — 2nd occurrence (non-consecutive to 1st)
    assert g.result is GameResult.ONGOING
    play(g, "Ke1", "Ke8")   # C — different intermediate position
    play(g, "Kd1", "Kd8")   # A — 3rd occurrence → DRAW
    assert g.result is GameResult.DRAW


def test_different_castling_rights_not_same_position():
    """Positions that differ only in castling rights must NOT be counted as equal."""
    from chess.domain.game_state import CastlingRights

    board = Board.empty()
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState()
    # White retains all castling rights at the start.
    g = Game(board=board, state=state)

    # We manually manipulate castling rights to simulate them changing between
    # otherwise identical positions, then verify no spurious draw is declared
    # when the piece placement and turn are equal but castling rights differ.
    snap1 = state.position_snapshot(board.position_key())
    state.white_castling.kingside = False
    snap2 = state.position_snapshot(board.position_key())

    assert snap1 != snap2, (
        "Positions differing only in castling rights must produce different snapshots"
    )


def test_different_en_passant_not_same_position():
    """Positions that differ only in the en passant target must NOT be counted as equal."""
    board = Board.empty()
    board.set(Position.from_algebraic("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(Position.from_algebraic("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState()
    state.white_castling.kingside = False
    state.white_castling.queenside = False
    state.black_castling.kingside = False
    state.black_castling.queenside = False

    key = board.position_key()
    snap_no_ep = state.position_snapshot(key)
    state.en_passant_target = Position.from_algebraic("e6")
    snap_with_ep = state.position_snapshot(key)

    assert snap_no_ep != snap_with_ep, (
        "Positions differing only in en passant target must produce different snapshots"
    )


def test_no_further_moves_after_threefold_draw():
    """Once a threefold draw is declared no further moves must be accepted."""
    board, state = _two_kings_board()
    g = Game(board=board, state=state)
    play(g, "Kd1", "Kd8", "Ke1", "Ke8")
    play(g, "Kd1", "Kd8", "Ke1", "Ke8")
    assert g.is_over()
    with pytest.raises(IllegalMoveError):
        play(g, "Kd1")
