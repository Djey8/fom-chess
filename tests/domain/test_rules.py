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
# Pawn promotion (UC-4)
# ---------------------------------------------------------------------------
def test_promotion_by_advance_generates_four_moves():
    """A pawn on the 7th rank advancing to the 8th produces 4 promotion moves."""
    board = Board.empty()
    board.set(_pos("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    # Move king away so e8 is free
    board.set(_pos("e8"), None)
    board.set(_pos("h8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("e7"), GameState())
    promo_moves = [m for m in moves if m.is_promotion]
    assert len(promo_moves) == 4
    from chess.domain.piece import PieceType as PT
    promo_types = {m.promotion for m in promo_moves}
    assert promo_types == {PT.QUEEN, PT.ROOK, PT.BISHOP, PT.KNIGHT}


def test_promotion_by_capture_generates_four_moves():
    """A pawn capturing onto the last rank produces 4 promotion moves per capture square."""
    from chess.domain.move import MoveKind
    board = Board.empty()
    board.set(_pos("d7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("d7"), GameState())
    capture_promos = [m for m in moves if m.kind is MoveKind.PROMOTION_CAPTURE]
    assert len(capture_promos) == 4
    assert all(m.captured is not None for m in capture_promos)


def test_promotion_advance_apply_replaces_pawn():
    """After applying a promotion move the target square holds the promoted piece."""
    from chess.domain.rules import apply_move
    from chess.domain.move import Move, MoveKind
    board = Board.empty()
    pawn = Piece(PieceType.PAWN, Color.WHITE)
    board.set(_pos("e7"), pawn)
    board.set(_pos("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h8"), Piece(PieceType.KING, Color.BLACK))
    move = Move(pawn, _pos("e7"), _pos("e8"), MoveKind.PROMOTION, promotion=PieceType.QUEEN)
    apply_move(board, move)
    assert board.is_empty(_pos("e7"))
    piece = board.get(_pos("e8"))
    assert piece is not None
    assert piece.type is PieceType.QUEEN
    assert piece.color is Color.WHITE


def test_pawn_cannot_remain_pawn_on_last_rank():
    """No non-promotion move is generated for a pawn reaching the last rank."""
    from chess.domain.move import MoveKind
    board = Board.empty()
    board.set(_pos("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("e7"), GameState())
    # All forward moves must be promotions
    non_promo = [m for m in moves if not m.is_promotion and m.target.algebraic == "e8"]
    assert non_promo == []


def test_promotion_delivers_check():
    """A promotion move that places the promoted piece giving check is detected."""
    board = Board.empty()
    # White pawn on d7, black king on h5, white king on a1
    board.set(_pos("d7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("a1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h5"), Piece(PieceType.KING, Color.BLACK))
    # After promoting to queen on d8, is black king in check? No (h5 vs d8 — no).
    # Instead: black king on d5, after d8=Q the queen on d8 attacks d5 via file.
    board.set(_pos("h5"), None)
    board.set(_pos("d5"), Piece(PieceType.KING, Color.BLACK))
    legal = generate_legal_moves(board, Color.WHITE, GameState())
    from chess.domain.rules import apply_move
    from chess.domain.move import Move, MoveKind
    pawn = board.get(_pos("d7"))
    queen_promo = Move(pawn, _pos("d7"), _pos("d8"), MoveKind.PROMOTION, promotion=PieceType.QUEEN)
    sim = board.clone()
    apply_move(sim, queen_promo)
    assert is_in_check(sim, Color.BLACK)
