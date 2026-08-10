"""Unit tests for UC-2: en passant capture.

Covers acceptance criteria AC-1 through AC-5 as defined in GitHub issue #5.
"""

from chess.application.game import Game
from chess.application.notation import format_move, parse_move
from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import CastlingRights, GameState
from chess.domain.move import MoveKind
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.domain.rules import generate_legal_moves, generate_pseudo_legal_moves_for


def _pos(square: str) -> Position:
    return Position.from_algebraic(square)


def _play(game: Game, *moves: str) -> None:
    for move_text in moves:
        move = parse_move(move_text, game)
        game.make_move(move)


# ---------------------------------------------------------------------------
# AC-1: En passant is included in legal moves when eligible
# ---------------------------------------------------------------------------

def test_ac1_en_passant_in_legal_moves_after_double_pawn_advance() -> None:
    """AC-1: Legal move list contains the en passant capture immediately after the double advance."""
    board = Board.empty()
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(
        turn=Color.WHITE,
        en_passant_target=_pos("d6"),
        white_castling=CastlingRights(False, False),
        black_castling=CastlingRights(False, False),
    )
    legal = generate_legal_moves(board, Color.WHITE, state)
    ep_moves = [m for m in legal if m.kind is MoveKind.EN_PASSANT]
    assert len(ep_moves) == 1
    assert ep_moves[0].target == _pos("d6")
    assert ep_moves[0].origin == _pos("e5")


def test_ac1_en_passant_via_game_notation() -> None:
    """AC-1: En passant move appears in legal moves after d7-d5 adjacent to e5 pawn."""
    game = Game()
    _play(game, "e4", "a6", "e5", "d5")
    move_notations = {format_move(m) for m in game.legal_moves() if m.origin == _pos("e5")}
    assert "exd6" in move_notations


# ---------------------------------------------------------------------------
# AC-2: En passant removes the captured pawn from its actual square
# ---------------------------------------------------------------------------

def test_ac2_captured_pawn_removed_from_original_square() -> None:
    """AC-2: The captured pawn is removed from d5, not d6, after exd6 en passant."""
    game = Game()
    _play(game, "e4", "a6", "e5", "d5", "exd6")
    assert game.board.is_empty(_pos("d5")), "Captured pawn must be removed from d5"
    assert game.board.get(_pos("d6")) is not None, "Capturing pawn must land on d6"
    assert game.board.is_empty(_pos("e5")), "Capturing pawn must leave e5"


def test_ac2_captured_pawn_piece_recorded_in_move() -> None:
    """AC-2: The move object records the captured pawn piece."""
    board = Board.empty()
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(
        turn=Color.WHITE,
        en_passant_target=_pos("d6"),
        white_castling=CastlingRights(False, False),
        black_castling=CastlingRights(False, False),
    )
    legal = generate_legal_moves(board, Color.WHITE, state)
    ep_move = next(m for m in legal if m.kind is MoveKind.EN_PASSANT)
    assert ep_move.captured is not None
    assert ep_move.captured.type is PieceType.PAWN
    assert ep_move.captured.color is Color.BLACK


# ---------------------------------------------------------------------------
# AC-3: En passant is no longer available after one full move passes
# ---------------------------------------------------------------------------

def test_ac3_en_passant_expires_after_one_move() -> None:
    """AC-3: The en passant capture is not in legal moves after any other move is played."""
    game = Game()
    _play(game, "e4", "a6", "e5", "d5")
    # White plays Nf3 instead of capturing en passant
    _play(game, "Nf3")
    # Black plays some move
    _play(game, "a5")
    ep_moves = [m for m in game.legal_moves() if m.kind is MoveKind.EN_PASSANT]
    assert ep_moves == [], "En passant must not be available after the immediate opportunity passes"


def test_ac3_en_passant_target_cleared_after_non_ep_move() -> None:
    """AC-3: en_passant_target is None after White plays a non-capturing move."""
    game = Game()
    _play(game, "e4", "a6", "e5", "d5")
    assert game.state.en_passant_target == _pos("d6")
    _play(game, "Nf3")
    assert game.state.en_passant_target is None


# ---------------------------------------------------------------------------
# AC-4: En passant target set correctly after two-square advance and cleared
# ---------------------------------------------------------------------------

def test_ac4_en_passant_target_set_after_double_advance() -> None:
    """AC-4: en_passant_target is set to the correct square after a two-square pawn push."""
    game = Game()
    _play(game, "e4")
    assert game.state.en_passant_target == _pos("e3"), (
        "After 1.e4, en_passant_target must be e3"
    )


def test_ac4_en_passant_target_not_set_for_single_advance() -> None:
    """AC-4: en_passant_target remains None after a single-square pawn advance."""
    game = Game()
    _play(game, "e3")
    assert game.state.en_passant_target is None


def test_ac4_en_passant_target_cleared_after_capture() -> None:
    """AC-4: en_passant_target is cleared once the en passant is played."""
    game = Game()
    _play(game, "e4", "a6", "e5", "d5", "exd6")
    assert game.state.en_passant_target is None


# ---------------------------------------------------------------------------
# AC-5: Pseudo-legal generation for position with en passant target
# ---------------------------------------------------------------------------

def test_ac5_pseudo_legal_includes_en_passant_move() -> None:
    """AC-5: generate_pseudo_legal_moves_for returns an EN_PASSANT move for the eligible pawn."""
    board = Board.empty()
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(en_passant_target=_pos("d6"))
    moves = generate_pseudo_legal_moves_for(board, _pos("e5"), state)
    ep_moves = [m for m in moves if m.kind is MoveKind.EN_PASSANT]
    assert len(ep_moves) == 1
    assert ep_moves[0].target.algebraic == "d6"


def test_ac5_no_en_passant_without_target() -> None:
    """AC-5: No EN_PASSANT moves generated when en_passant_target is None."""
    board = Board.empty()
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState()  # en_passant_target is None
    moves = generate_pseudo_legal_moves_for(board, _pos("e5"), state)
    assert not any(m.kind is MoveKind.EN_PASSANT for m in moves)
