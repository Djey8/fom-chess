"""Fixed acceptance-test suite for UC-6 (draw by threefold repetition).

See tests/acceptance/test_uc2_en_passant.py for the rationale: this suite is
part of the frozen thesis baseline `thesis-baseline-2026-08-10` and is not
written by whoever implements the ticket (manual or agent).

Per Epic UC-1's own sequencing note, UC-6 depends on UC-2 (en passant state)
and UC-3 (castling-rights state) already being implemented -- AC2 and AC3
below only become meaningful once those exist.

All tests are expected to fail until UC-6 (and, for AC2/AC3, UC-2/UC-3) are
implemented.
"""

import pytest

from chess.application.game import Game, GameResult, IllegalMoveError
from chess.application.notation import parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import CastlingRights, GameState
from chess.domain.move import Move, MoveKind
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.presentation.console import ConsoleUI


def _pos(square: str) -> Position:
    return Position.from_algebraic(square)


def _play(game: Game, *moves: str) -> None:
    for move_text in moves:
        move = parse_move(move_text, game)
        game.make_move(move)


def _bogus_move_for_any_piece(game: Game) -> Move:
    piece_pos, piece = next(game.board.iter_pieces())
    return Move(piece, piece_pos, piece_pos, MoveKind.NORMAL)


def _knight_shuffle_setup() -> Game:
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("g1"), Piece(PieceType.KNIGHT, Color.WHITE))
    board.set(_pos("g8"), Piece(PieceType.KNIGHT, Color.BLACK))
    state = GameState(
        white_castling=CastlingRights(False, False),
        black_castling=CastlingRights(False, False),
    )
    return Game(board=board, state=state)


_XFAIL = pytest.mark.xfail(
    reason="Threefold repetition detection (UC-6) is not implemented yet (thesis baseline).",
    strict=False,
)


# ---------------------------------------------------------------------------
# AC1 -- same position for the third time -> draw, no further moves
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac1_threefold_repetition_declares_draw():
    game = _knight_shuffle_setup()
    _play(game, "Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8")
    assert game.result is GameResult.DRAW


@_XFAIL
def test_ac1_no_further_moves_accepted_after_threefold_draw():
    game = _knight_shuffle_setup()
    _play(game, "Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8")
    assert game.result is GameResult.DRAW
    with pytest.raises(IllegalMoveError):
        game.make_move(_bogus_move_for_any_piece(game))


# ---------------------------------------------------------------------------
# AC2 -- positions differing only in castling rights are NOT the same
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac2_positions_differing_only_in_castling_rights_not_counted_as_repetition():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("b1"), Piece(PieceType.KNIGHT, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)

    # Occurrence #1 of "Ke1, Rh1, Nb1, Ke8, White to move": reached via a
    # neutral knight round trip, so castling rights stay True.
    _play(game, "b1c3", "e8d8", "c3b1", "d8e8")

    # Occurrence #2: the rook round-trips away and back, permanently
    # revoking kingside rights on the way out -- same piece placement,
    # rights now False.
    _play(game, "h1g1", "e8d8", "g1h1", "d8e8")

    # Occurrence #3: same rook round trip again; rights already False.
    _play(game, "h1g1", "e8d8", "g1h1", "d8e8")

    # The piece placement recurred 3 times, but only 2 of those (#2, #3)
    # share identical castling rights with each other -- must NOT be a draw.
    assert game.result is GameResult.ONGOING


# ---------------------------------------------------------------------------
# AC3 -- positions differing only in the en passant target are NOT the same
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac3_positions_differing_only_in_en_passant_target_not_counted_as_repetition():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a2"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    game = Game(board=board)

    # Occurrence #1: right after the double-square advance,
    # en_passant_target == a3.
    _play(game, "a2a4", "e8d8", "e1d1", "d8e8", "d1e1")

    # Occurrences #2 and #3: identical piece placement, but the en passant
    # right has long since expired (target is None).
    _play(game, "e8d8", "e1d1", "d8e8", "d1e1")
    _play(game, "e8d8", "e1d1", "d8e8", "d1e1")

    assert game.result is GameResult.ONGOING


# ---------------------------------------------------------------------------
# AC4 -- repetitions need not be consecutive / reached the same way
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac4_non_consecutive_repetition_still_detected():
    game = _knight_shuffle_setup()
    # Same position recurs 3 times (including the start position), but the
    # second and third occurrence are reached via two DIFFERENT knight
    # paths (g1-f3-g1 vs g1-h3-g1).
    _play(game, "Nf3", "Nf6", "Ng1", "Ng8")
    _play(game, "Nh3", "Nh6", "Ng1", "Ng8")
    assert game.result is GameResult.DRAW


# ---------------------------------------------------------------------------
# AC5 -- the UI displays a threefold-repetition draw message
# ---------------------------------------------------------------------------
@_XFAIL
def test_ac5_ui_displays_threefold_repetition_message():
    moves = iter(["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8", "quit"])
    outputs: list[str] = []
    ui = ConsoleUI(
        game=_knight_shuffle_setup(),
        input_fn=lambda _: next(moves),
        output_fn=outputs.append,
        colored=False,
    )
    ui.run()
    assert "repetition" in "\n".join(outputs).lower()
