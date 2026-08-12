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
# UC-5: Checkmate and stalemate detection
# ---------------------------------------------------------------------------

def _board_from_pieces(pieces: dict[str, tuple[PieceType, Color]]) -> Board:
    """Build a board from a mapping ``algebraic -> (PieceType, Color)``."""
    board = Board.empty()
    for alg, (pt, color) in pieces.items():
        board.set(Position.from_algebraic(alg), Piece(pt, color))
    return board


# --- Checkmate positions ---

def test_checkmate_fools_mate():
    """Fool's mate: quickest checkmate in chess (two moves, black wins)."""
    g = Game()
    play(g, "f3", "e5", "g4", "Qh4")
    assert g.result is GameResult.BLACK_WINS
    assert g.is_over()


def test_checkmate_back_rank():
    """Back-rank checkmate: white rook delivers checkmate on rank 8."""
    board = _board_from_pieces({
        "g6": (PieceType.KING, Color.WHITE),
        "a1": (PieceType.ROOK, Color.WHITE),
        "h8": (PieceType.KING, Color.BLACK),
    })
    g = Game(board=board)
    # Ra8# — black king on h8 is checked by the rook along rank 8;
    # g8 is covered by the rook, g7 and h7 are covered by the white king on g6.
    play(g, "Ra8")
    assert g.result is GameResult.WHITE_WINS
    assert g.is_over()


def test_checkmate_smothered_like():
    """Ladder mate: two rooks cut off the black king."""
    board = _board_from_pieces({
        "e6": (PieceType.KING, Color.WHITE),
        "a7": (PieceType.ROOK, Color.WHITE),
        "b1": (PieceType.ROOK, Color.WHITE),
        "h8": (PieceType.KING, Color.BLACK),
    })
    g = Game(board=board)
    # Rb8# — the rook on b1 moves to b8 giving check along rank 8;
    # g8 is covered by the new rook, h7 and g7 are covered by Ra7 on rank 7.
    play(g, "Rb8")
    assert g.result is GameResult.WHITE_WINS
    assert g.is_over()


def test_cannot_play_after_checkmate():
    """Moves must be rejected once the game has ended by checkmate."""
    g = Game()
    play(g, "f3", "e5", "g4", "Qh4")
    assert g.is_over()
    with pytest.raises((IllegalMoveError, Exception)):
        play(g, "e4")


# --- Stalemate positions ---

def test_stalemate_king_in_corner():
    """Classic queen-and-king vs king stalemate: black king trapped in corner."""
    # White: king d5, queen g6.  White plays Qb6.
    # After Qb6: Ka8 has no legal moves (b8/a7/b7 all attacked by Qb6) and
    # is not in check (queen on b6 does not attack a8 by rank, file, or diagonal).
    board = _board_from_pieces({
        "d5": (PieceType.KING, Color.WHITE),
        "g6": (PieceType.QUEEN, Color.WHITE),
        "a8": (PieceType.KING, Color.BLACK),
    })
    g = Game(board=board)
    play(g, "Qb6")
    assert g.result is GameResult.STALEMATE
    assert g.is_over()


def test_stalemate_queen_only():
    """White queen alone can create stalemate against a corner king."""
    board = _board_from_pieces({
        "c6": (PieceType.KING, Color.WHITE),
        "b1": (PieceType.QUEEN, Color.WHITE),
        "a8": (PieceType.KING, Color.BLACK),
    })
    g = Game(board=board)
    # Qb6 — black king on a8 has no legal moves and is not in check.
    play(g, "Qb6")
    assert g.result is GameResult.STALEMATE
    assert g.is_over()


# --- Near-stalemate: legal move still exists ---

def test_near_stalemate_legal_move_exists():
    """Black still has a legal pawn move — game must stay ONGOING."""
    board = _board_from_pieces({
        "c6": (PieceType.KING, Color.WHITE),
        "b1": (PieceType.QUEEN, Color.WHITE),
        "a8": (PieceType.KING, Color.BLACK),
        "h7": (PieceType.PAWN, Color.BLACK),   # escape: h7h6 or h7h5
    })
    g = Game(board=board)
    play(g, "Qb6")
    assert g.result is GameResult.ONGOING
    assert not g.is_over()
