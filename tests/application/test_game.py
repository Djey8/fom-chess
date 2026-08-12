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
# UC-5 Checkmate and stalemate detection
# ---------------------------------------------------------------------------

def _board_with(*piece_specs: tuple[str, Piece]) -> Board:
    """Build an empty board and place pieces at the given algebraic squares."""
    board = Board.empty()
    for square, piece in piece_specs:
        board.set(Position.from_algebraic(square), piece)
    return board


def _W(pt: PieceType) -> Piece:  # noqa: N802
    return Piece(pt, Color.WHITE)


def _B(pt: PieceType) -> Piece:  # noqa: N802
    return Piece(pt, Color.BLACK)


# -- Checkmate positions ---------------------------------------------------

def test_checkmate_scholars_mate():
    """Scholar's mate (1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6?? 4.Qxf7#)."""
    g = Game()
    play(g, "e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7")
    assert g.result is GameResult.WHITE_WINS
    assert g.is_over()


def test_checkmate_fools_mate():
    """Fool's mate — fastest checkmate (1.f3 e5 2.g4 Qh4#)."""
    g = Game()
    play(g, "f3", "e5", "g4", "Qh4")
    assert g.result is GameResult.BLACK_WINS
    assert g.is_over()


def test_checkmate_back_rank():
    """Back-rank checkmate: white queen delivers checkmate on the 8th rank."""
    # White: king h1, queen a8 (just delivered); Black: king h8, pawns g7/h7
    board = _board_with(
        ("h1", _W(PieceType.KING)),
        ("a1", _W(PieceType.QUEEN)),
        ("h8", _B(PieceType.KING)),
        ("g7", _B(PieceType.PAWN)),
        ("h7", _B(PieceType.PAWN)),
    )
    # White to move — play Qa8#
    g = Game(board=board)
    play(g, "Qa8")
    assert g.result is GameResult.WHITE_WINS
    assert g.is_over()


def test_cannot_play_after_checkmate():
    """After checkmate no further moves may be played."""
    g = Game()
    play(g, "f3", "e5", "g4", "Qh4")
    assert g.is_over()
    # parse_move raises NotationError (no legal moves) or make_move raises
    # IllegalMoveError — both satisfy the contract that the game is frozen.
    with pytest.raises(Exception):
        play(g, "Nf3")


# -- Stalemate positions ---------------------------------------------------

def test_stalemate_cornered_king():
    """Classic stalemate: lone black king in corner with no legal move, not in check."""
    # Pre-move: white king f4, white queen a6, black king h8.
    # White plays Qg6 — queen slides along rank 6 (path a6-g6 is clear because
    # the king is on f4, not f6) and covers g8/h7/g7 without checking h8.
    board = _board_with(
        ("f4", _W(PieceType.KING)),
        ("a6", _W(PieceType.QUEEN)),
        ("h8", _B(PieceType.KING)),
    )
    g = Game(board=board)
    play(g, "Qg6")  # g8/h7/g7 all covered — black king stalemated on h8
    assert g.result is GameResult.STALEMATE
    assert g.is_over()


def test_stalemate_queen_trap():
    """Another stalemate: black king on a8, white king on c4, queen slides to b6."""
    # After Qb6: black king a8 cannot move to a7 (diagonal attack from b6),
    # b8 (vertical attack from b6), or b7 (vertical/diagonal attack from b6).
    # Queen on b6 does NOT check a8 (no straight or diagonal ray from b6 to a8).
    # King is on c4 (not c6) so the h6-b6 path along rank 6 is clear.
    board = _board_with(
        ("c4", _W(PieceType.KING)),
        ("h6", _W(PieceType.QUEEN)),
        ("a8", _B(PieceType.KING)),
    )
    g = Game(board=board)
    play(g, "Qb6")  # queen slides along rank 6 → black king a8 is stalemated
    assert g.result is GameResult.STALEMATE
    assert g.is_over()


def test_near_stalemate_legal_move_exists():
    """Near-stalemate: position looks close but black still has one legal king move."""
    # White: king f6, queen g5. Black: king h8. Black can still play Kg8.
    board = _board_with(
        ("f6", _W(PieceType.KING)),
        ("g5", _W(PieceType.QUEEN)),
        ("h8", _B(PieceType.KING)),
    )
    state = GameState(turn=Color.BLACK)
    g = Game(board=board, state=state)
    assert not g.is_over()
    assert g.result is GameResult.ONGOING
    # Black has at least one legal move (Kg8 is safe — queen on g5 doesn't cover g8
    # but we only assert the game is not over)
    assert bool(g.legal_moves(Color.BLACK))
