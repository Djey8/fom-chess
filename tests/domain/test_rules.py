"""Rule-level tests covering move generation, check, mate, and stalemate."""

from chess.domain.board import Board
from chess.domain.color import Color
from chess.domain.game_state import GameState
from chess.domain.piece import Piece, PieceType
from chess.domain.position import Position
from chess.domain.rules import (
    generate_legal_moves,
    generate_pseudo_legal_moves_for,
    is_in_check,
    is_square_attacked,
)


def _pos(s: str) -> Position:
    return Position.from_algebraic(s)


# ---------------------------------------------------------------------------
# Pawn
# ---------------------------------------------------------------------------
def test_white_pawn_initial_moves():
    board = Board.standard()
    state = GameState()
    moves = generate_pseudo_legal_moves_for(board, _pos("e2"), state)
    targets = {m.target.algebraic for m in moves}
    assert targets == {"e3", "e4"}


def test_pawn_blocked_cannot_move():
    board = Board.empty()
    board.set(_pos("e2"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e3"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("e2"), GameState())
    assert moves == []


def test_pawn_captures_diagonally():
    board = Board.empty()
    board.set(_pos("d4"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    targets = {m.target.algebraic for m in generate_pseudo_legal_moves_for(board, _pos("d4"), GameState())}
    assert "e5" in targets
    assert "d5" in targets


def test_pawn_cannot_capture_forward():
    board = Board.empty()
    board.set(_pos("e4"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("e4"), GameState())
    assert all(m.target.algebraic != "e5" for m in moves)


# ---------------------------------------------------------------------------
# Pieces
# ---------------------------------------------------------------------------
def test_knight_l_moves_from_d4():
    board = Board.empty()
    board.set(_pos("d4"), Piece(PieceType.KNIGHT, Color.WHITE))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    targets = {m.target.algebraic for m in generate_pseudo_legal_moves_for(board, _pos("d4"), GameState())}
    assert targets == {"b3", "b5", "c2", "c6", "e2", "e6", "f3", "f5"}


def test_bishop_blocked_at_start():
    board = Board.standard()
    moves = generate_pseudo_legal_moves_for(board, _pos("c1"), GameState())
    assert moves == []


def test_rook_blocked_at_start():
    board = Board.standard()
    moves = generate_pseudo_legal_moves_for(board, _pos("a1"), GameState())
    assert moves == []


def test_queen_combines_rook_and_bishop():
    board = Board.empty()
    board.set(_pos("d4"), Piece(PieceType.QUEEN, Color.WHITE))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    targets = {m.target.algebraic for m in generate_pseudo_legal_moves_for(board, _pos("d4"), GameState())}
    # 14 + 13 = 27 for an unobstructed queen (minus squares blocked by own king at e1)
    # Rather than hardcoding 27, sanity-check key squares exist.
    for sq in ("a4", "h4", "d1", "d8", "a1", "h8", "a7", "g1"):
        assert sq in targets or sq == "e1"  # e1 is the king's square


# ---------------------------------------------------------------------------
# Attack / check
# ---------------------------------------------------------------------------
def test_is_square_attacked_by_rook():
    board = Board.empty()
    board.set(_pos("a1"), Piece(PieceType.ROOK, Color.WHITE))
    assert is_square_attacked(board, _pos("a8"), Color.WHITE)
    assert is_square_attacked(board, _pos("h1"), Color.WHITE)
    assert not is_square_attacked(board, _pos("b2"), Color.WHITE)


def test_pinned_piece_cannot_expose_king():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e2"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    legal = generate_legal_moves(board, Color.WHITE, state)
    # The pinned rook can only move along the e-file.
    rook_moves = [m for m in legal if m.origin == _pos("e2")]
    for m in rook_moves:
        assert m.target.file == "e"


def test_checkmate_detected():
    # Fool's mate position after 1.f3 e5 2.g4 Qh4#
    board = Board.standard()
    # Manually mutate: f2->f3, e7->e5, g2->g4, d8->h4
    from chess.domain.rules import apply_move
    from chess.domain.move import Move, MoveKind

    def do(origin, target, kind=MoveKind.NORMAL):
        piece = board.get(_pos(origin))
        apply_move(board, Move(piece, _pos(origin), _pos(target), kind))

    do("f2", "f3")
    do("e7", "e5")
    do("g2", "g4", MoveKind.DOUBLE_PAWN)
    do("d8", "h4")

    assert is_in_check(board, Color.WHITE)
    legal = generate_legal_moves(board, Color.WHITE, GameState(turn=Color.WHITE))
    assert legal == []


def test_stalemate_position():
    # Classic stalemate: black king a8, white king c7 (illegal adjacency? Use valid setup)
    # Use: Black king h8, White king f7, White queen g6. Black to move, no legal move, not in check.
    board = Board.empty()
    board.set(_pos("h8"), Piece(PieceType.KING, Color.BLACK))
    board.set(_pos("f7"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("g6"), Piece(PieceType.QUEEN, Color.WHITE))
    state = GameState(turn=Color.BLACK)
    assert not is_in_check(board, Color.BLACK)
    legal = generate_legal_moves(board, Color.BLACK, state)
    assert legal == []



# ---------------------------------------------------------------------------
# Castling
# ---------------------------------------------------------------------------
def _setup_castling_board(color: Color, kingside: bool = True, queenside: bool = True) -> Board:
    """Return a board with only king and rook(s) on back rank for castling tests."""
    board = Board.empty()
    row = 7 if color is Color.WHITE else 0
    # Place the king
    board.set(Position(row, 4), Piece(PieceType.KING, color))
    # Add opponent king so the board is technically valid
    opp_row = 0 if color is Color.WHITE else 7
    board.set(Position(opp_row, 4), Piece(PieceType.KING, color.opponent))
    if kingside:
        board.set(Position(row, 7), Piece(PieceType.ROOK, color))
    if queenside:
        board.set(Position(row, 0), Piece(PieceType.ROOK, color))
    return board


def _castling_state(color: Color, kingside: bool = True, queenside: bool = True) -> GameState:
    from chess.domain.game_state import CastlingRights
    state = GameState(turn=color)
    rights = state.castling_rights(color)
    rights.kingside = kingside
    rights.queenside = queenside
    return state


def test_white_kingside_castling_included():
    board = _setup_castling_board(Color.WHITE, kingside=True, queenside=False)
    state = _castling_state(Color.WHITE, kingside=True, queenside=False)
    moves = generate_legal_moves(board, Color.WHITE, state)
    targets = {m.target.algebraic for m in moves if m.is_castle}
    assert "g1" in targets


def test_white_queenside_castling_included():
    board = _setup_castling_board(Color.WHITE, kingside=False, queenside=True)
    state = _castling_state(Color.WHITE, kingside=False, queenside=True)
    moves = generate_legal_moves(board, Color.WHITE, state)
    targets = {m.target.algebraic for m in moves if m.is_castle}
    assert "c1" in targets


def test_black_kingside_castling_included():
    board = _setup_castling_board(Color.BLACK, kingside=True, queenside=False)
    state = _castling_state(Color.BLACK, kingside=True, queenside=False)
    moves = generate_legal_moves(board, Color.BLACK, state)
    targets = {m.target.algebraic for m in moves if m.is_castle}
    assert "g8" in targets


def test_black_queenside_castling_included():
    board = _setup_castling_board(Color.BLACK, kingside=False, queenside=True)
    state = _castling_state(Color.BLACK, kingside=False, queenside=True)
    moves = generate_legal_moves(board, Color.BLACK, state)
    targets = {m.target.algebraic for m in moves if m.is_castle}
    assert "c8" in targets


def test_castling_blocked_by_piece_between():
    board = _setup_castling_board(Color.WHITE, kingside=True, queenside=True)
    # Block f1
    board.set(_pos("f1"), Piece(PieceType.BISHOP, Color.WHITE))
    state = _castling_state(Color.WHITE, kingside=True, queenside=True)
    moves = generate_legal_moves(board, Color.WHITE, state)
    castle_targets = {m.target.algebraic for m in moves if m.is_castle}
    assert "g1" not in castle_targets


def test_castling_not_allowed_when_no_rights():
    board = _setup_castling_board(Color.WHITE, kingside=True, queenside=True)
    state = _castling_state(Color.WHITE, kingside=False, queenside=False)
    moves = generate_legal_moves(board, Color.WHITE, state)
    assert not any(m.is_castle for m in moves)


def test_castling_not_allowed_when_in_check():
    board = _setup_castling_board(Color.WHITE, kingside=True, queenside=True)
    # Place enemy rook attacking e1
    board.set(_pos("e8"), Piece(PieceType.ROOK, Color.BLACK))
    state = _castling_state(Color.WHITE, kingside=True, queenside=True)
    moves = generate_legal_moves(board, Color.WHITE, state)
    assert not any(m.is_castle for m in moves)


def test_castling_not_allowed_through_attacked_square():
    board = _setup_castling_board(Color.WHITE, kingside=True, queenside=False)
    # Attack f1 (transit square for kingside)
    board.set(_pos("f8"), Piece(PieceType.ROOK, Color.BLACK))
    state = _castling_state(Color.WHITE, kingside=True, queenside=False)
    moves = generate_legal_moves(board, Color.WHITE, state)
    castle_targets = {m.target.algebraic for m in moves if m.is_castle}
    assert "g1" not in castle_targets


def test_castling_not_allowed_landing_on_attacked_square():
    board = _setup_castling_board(Color.WHITE, kingside=True, queenside=False)
    # Attack g1 (king landing square for kingside)
    board.set(_pos("g8"), Piece(PieceType.ROOK, Color.BLACK))
    state = _castling_state(Color.WHITE, kingside=True, queenside=False)
    moves = generate_legal_moves(board, Color.WHITE, state)
    castle_targets = {m.target.algebraic for m in moves if m.is_castle}
    assert "g1" not in castle_targets


def test_castling_rook_relocated_kingside():
    from chess.domain.rules import apply_move
    from chess.domain.move import MoveKind
    board = _setup_castling_board(Color.WHITE, kingside=True, queenside=False)
    king = board.get(_pos("e1"))
    move = apply_move(board, __import__('chess.domain.move', fromlist=['Move']).Move(
        king, _pos("e1"), _pos("g1"), MoveKind.CASTLE_KINGSIDE
    ))
    assert board.get(_pos("g1")) == Piece(PieceType.KING, Color.WHITE)
    assert board.get(_pos("f1")) == Piece(PieceType.ROOK, Color.WHITE)
    assert board.is_empty(_pos("e1"))
    assert board.is_empty(_pos("h1"))


def test_castling_rook_relocated_queenside():
    from chess.domain.rules import apply_move
    from chess.domain.move import MoveKind, Move
    board = _setup_castling_board(Color.WHITE, kingside=False, queenside=True)
    king = board.get(_pos("e1"))
    apply_move(board, Move(king, _pos("e1"), _pos("c1"), MoveKind.CASTLE_QUEENSIDE))
    assert board.get(_pos("c1")) == Piece(PieceType.KING, Color.WHITE)
    assert board.get(_pos("d1")) == Piece(PieceType.ROOK, Color.WHITE)
    assert board.is_empty(_pos("e1"))
    assert board.is_empty(_pos("a1"))
