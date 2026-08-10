"""Rule-level tests covering move generation, check, mate, stalemate, special moves."""

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


def test_pawn_promotion_generates_four_choices():
    board = Board.empty()
    board.set(_pos("e7"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    moves = generate_pseudo_legal_moves_for(board, _pos("e7"), GameState())
    promos = [m for m in moves if m.is_promotion]
    assert len(promos) == 4
    assert {m.promotion for m in promos} == {
        PieceType.QUEEN,
        PieceType.ROOK,
        PieceType.BISHOP,
        PieceType.KNIGHT,
    }


def test_en_passant_available():
    board = Board.empty()
    board.set(_pos("e5"), Piece(PieceType.PAWN, Color.WHITE))
    board.set(_pos("d5"), Piece(PieceType.PAWN, Color.BLACK))
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(en_passant_target=_pos("d6"))
    moves = generate_pseudo_legal_moves_for(board, _pos("e5"), state)
    assert any(m.target.algebraic == "d6" and m.captured is not None for m in moves)


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
def test_white_kingside_castling_available():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert any(m.target.algebraic == "g1" for m in moves)


def test_castling_blocked_when_king_in_check():
    board = Board.empty()
    board.set(_pos("e1"), Piece(PieceType.KING, Color.WHITE))
    board.set(_pos("h1"), Piece(PieceType.ROOK, Color.WHITE))
    board.set(_pos("e8"), Piece(PieceType.ROOK, Color.BLACK))
    board.set(_pos("a8"), Piece(PieceType.KING, Color.BLACK))
    state = GameState(turn=Color.WHITE)
    moves = generate_pseudo_legal_moves_for(board, _pos("e1"), state)
    assert all(m.target.algebraic != "g1" for m in moves)
