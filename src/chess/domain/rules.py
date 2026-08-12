"""Chess rules: pseudo-legal move generation, attacks, and legality filtering.

Separation of concerns:
    * ``generate_pseudo_legal_moves`` produces all moves following piece movement
      rules but without considering king safety.
    * ``is_square_attacked`` asks whether a square is attacked by a given color.
    * ``generate_legal_moves`` filters pseudo-legal moves by simulating them on a
      board clone and rejecting any that leave the mover's king in check.

The ``GameState`` passes castling rights and the current en-passant target so
that special moves can be generated.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable, Optional

from .board import Board
from .color import Color
from .move import Move, MoveKind
from .piece import Piece, PieceType
from .position import Position

if TYPE_CHECKING:
    from .game_state import GameState

_log = logging.getLogger(__name__)

KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
KING_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
QUEEN_DIRS = BISHOP_DIRS + ROOK_DIRS


# ---------------------------------------------------------------------------
# Attack detection
# ---------------------------------------------------------------------------
def is_square_attacked(board: Board, square: Position, by_color: Color) -> bool:
    """Return ``True`` if any piece of ``by_color`` attacks ``square``."""
    # Pawn attacks
    pawn_dir = -by_color.forward_direction  # attackers move opposite to targets
    for dcol in (-1, 1):
        src = square.offset(pawn_dir, dcol)
        if src is not None:
            piece = board.get(src)
            if piece is not None and piece.color is by_color and piece.type is PieceType.PAWN:
                return True

    # Knights
    for dr, dc in KNIGHT_OFFSETS:
        src = square.offset(dr, dc)
        if src is not None:
            piece = board.get(src)
            if piece is not None and piece.color is by_color and piece.type is PieceType.KNIGHT:
                return True

    # King (adjacent)
    for dr, dc in KING_OFFSETS:
        src = square.offset(dr, dc)
        if src is not None:
            piece = board.get(src)
            if piece is not None and piece.color is by_color and piece.type is PieceType.KING:
                return True

    # Sliding pieces (bishop/rook/queen)
    for dirs, sliders in (
        (BISHOP_DIRS, (PieceType.BISHOP, PieceType.QUEEN)),
        (ROOK_DIRS, (PieceType.ROOK, PieceType.QUEEN)),
    ):
        for dr, dc in dirs:
            r, c = square.row + dr, square.col + dc
            while 0 <= r <= 7 and 0 <= c <= 7:
                p = board.get(Position(r, c))
                if p is not None:
                    if p.color is by_color and p.type in sliders:
                        return True
                    break
                r += dr
                c += dc

    return False


def is_in_check(board: Board, color: Color) -> bool:
    king_pos = board.find_king(color)
    if king_pos is None:
        return False
    return is_square_attacked(board, king_pos, color.opponent)


# ---------------------------------------------------------------------------
# Pseudo-legal move generation per piece
# ---------------------------------------------------------------------------
def _sliding_moves(
    board: Board, origin: Position, piece: Piece, directions: Iterable[tuple[int, int]]
) -> list[Move]:
    moves: list[Move] = []
    for dr, dc in directions:
        r, c = origin.row + dr, origin.col + dc
        while 0 <= r <= 7 and 0 <= c <= 7:
            target = Position(r, c)
            occupant = board.get(target)
            if occupant is None:
                moves.append(Move(piece, origin, target, MoveKind.NORMAL))
            else:
                if occupant.color is not piece.color:
                    moves.append(
                        Move(piece, origin, target, MoveKind.CAPTURE, captured=occupant)
                    )
                break
            r += dr
            c += dc
    return moves


def _step_moves(
    board: Board, origin: Position, piece: Piece, offsets: Iterable[tuple[int, int]]
) -> list[Move]:
    moves: list[Move] = []
    for dr, dc in offsets:
        target = origin.offset(dr, dc)
        if target is None:
            continue
        occupant = board.get(target)
        if occupant is None:
            moves.append(Move(piece, origin, target, MoveKind.NORMAL))
        elif occupant.color is not piece.color:
            moves.append(Move(piece, origin, target, MoveKind.CAPTURE, captured=occupant))
    return moves


def _pawn_moves(
    board: Board,
    origin: Position,
    piece: Piece,
    en_passant_target: Optional[Position],
) -> list[Move]:
    # NOTE (thesis baseline `thesis-baseline-2026-08-10`): en passant (UC-2) and
    # pawn promotion (UC-4) are intentionally not implemented yet. A pawn
    # reaching the last rank simply moves/captures there and remains a pawn;
    # ``en_passant_target`` is accepted for interface compatibility but unused.
    del en_passant_target
    moves: list[Move] = []
    direction = piece.color.forward_direction
    start_row = 6 if piece.color is Color.WHITE else 1

    # Forward one
    one_ahead = origin.offset(direction, 0)
    if one_ahead is not None and board.is_empty(one_ahead):
        moves.append(Move(piece, origin, one_ahead, MoveKind.NORMAL))
        # Forward two from start
        if origin.row == start_row:
            two_ahead = origin.offset(2 * direction, 0)
            if two_ahead is not None and board.is_empty(two_ahead):
                moves.append(Move(piece, origin, two_ahead, MoveKind.DOUBLE_PAWN))

    # Diagonal captures
    for dcol in (-1, 1):
        target = origin.offset(direction, dcol)
        if target is None:
            continue
        occupant = board.get(target)
        if occupant is not None and occupant.color is not piece.color:
            moves.append(
                Move(piece, origin, target, MoveKind.CAPTURE, captured=occupant)
            )

    return moves


# ---------------------------------------------------------------------------
# Castling pseudo-legal move generation
# ---------------------------------------------------------------------------

# Home squares by color: (king_col, kingside_rook_col, queenside_rook_col, back_row)
_CASTLE_CONFIG = {
    Color.WHITE: (4, 7, 0, 7),
    Color.BLACK: (4, 7, 0, 0),
}

# Columns that must be empty between king and rook
_KINGSIDE_EMPTY_COLS = (5, 6)   # f and g files
_QUEENSIDE_EMPTY_COLS = (1, 2, 3)  # b, c, d files

# Squares the king passes through / lands on (must not be attacked)
_KINGSIDE_KING_COLS = (4, 5, 6)   # e, f, g files
_QUEENSIDE_KING_COLS = (4, 3, 2)  # e, d, c files


def _castling_moves(
    board: Board,
    origin: Position,
    piece: Piece,
    state: "GameState",
) -> list[Move]:
    """Return pseudo-legal castling moves for *piece* (a king) at *origin*.

    Checks are included here so that illegal castling is already excluded at the
    pseudo-legal stage, matching the FIDE rule that the king must not be in check,
    pass through, or land on an attacked square.
    """
    moves: list[Move] = []
    color = piece.color
    king_col, ks_rook_col, qs_rook_col, back_row = _CASTLE_CONFIG[color]

    # King must be on its original square.
    if origin.row != back_row or origin.col != king_col:
        _log.debug("Castling rejected: king not on home square (%s)", origin.algebraic)
        return moves

    rights = state.castling_rights(color)
    opponent = color.opponent

    # --- Kingside ---
    if rights.kingside:
        rook_sq = Position(back_row, ks_rook_col)
        rook = board.get(rook_sq)
        empty_ok = all(board.is_empty(Position(back_row, c)) for c in _KINGSIDE_EMPTY_COLS)
        safe_ok = all(
            not is_square_attacked(board, Position(back_row, c), opponent)
            for c in _KINGSIDE_KING_COLS
        )
        rook_ok = rook is not None and rook.type is PieceType.ROOK and rook.color is color
        if rook_ok and empty_ok and safe_ok:
            _log.debug("Castling accepted: %s kingside", color.value)
            target = Position(back_row, 6)
            moves.append(Move(piece, origin, target, MoveKind.CASTLE_KINGSIDE))
        else:
            _log.debug(
                "Castling rejected: %s kingside (rook_ok=%s, empty=%s, safe=%s)",
                color.value, rook_ok, empty_ok, safe_ok,
            )

    # --- Queenside ---
    if rights.queenside:
        rook_sq = Position(back_row, qs_rook_col)
        rook = board.get(rook_sq)
        empty_ok = all(board.is_empty(Position(back_row, c)) for c in _QUEENSIDE_EMPTY_COLS)
        safe_ok = all(
            not is_square_attacked(board, Position(back_row, c), opponent)
            for c in _QUEENSIDE_KING_COLS
        )
        rook_ok = rook is not None and rook.type is PieceType.ROOK and rook.color is color
        if rook_ok and empty_ok and safe_ok:
            _log.debug("Castling accepted: %s queenside", color.value)
            target = Position(back_row, 2)
            moves.append(Move(piece, origin, target, MoveKind.CASTLE_QUEENSIDE))
        else:
            _log.debug(
                "Castling rejected: %s queenside (rook_ok=%s, empty=%s, safe=%s)",
                color.value, rook_ok, empty_ok, safe_ok,
            )

    return moves


def generate_pseudo_legal_moves_for(
    board: Board, origin: Position, state: "GameState"
) -> list[Move]:
    piece = board.get(origin)
    if piece is None:
        return []
    pt = piece.type
    if pt is PieceType.PAWN:
        return _pawn_moves(board, origin, piece, state.en_passant_target)
    if pt is PieceType.KNIGHT:
        return _step_moves(board, origin, piece, KNIGHT_OFFSETS)
    if pt is PieceType.BISHOP:
        return _sliding_moves(board, origin, piece, BISHOP_DIRS)
    if pt is PieceType.ROOK:
        return _sliding_moves(board, origin, piece, ROOK_DIRS)
    if pt is PieceType.QUEEN:
        return _sliding_moves(board, origin, piece, QUEEN_DIRS)
    if pt is PieceType.KING:
        moves = _step_moves(board, origin, piece, KING_OFFSETS)
        moves.extend(_castling_moves(board, origin, piece, state))
        return moves
    return []


def generate_pseudo_legal_moves(board: Board, color: Color, state: "GameState") -> list[Move]:
    moves: list[Move] = []
    for pos, piece in board.iter_pieces():
        if piece.color is color:
            moves.extend(generate_pseudo_legal_moves_for(board, pos, state))
    return moves


# ---------------------------------------------------------------------------
# Legality filter
# ---------------------------------------------------------------------------
def apply_move(board: Board, move: Move) -> None:
    """Mutate ``board`` by applying ``move``. Used for both real play and simulation.

    Handles normal moves, captures, and castling (rook relocation).
    """
    board.set(move.origin, None)
    board.set(move.target, move.piece)

    if move.kind is MoveKind.CASTLE_KINGSIDE:
        # Move rook from h-file to f-file on the same rank.
        row = move.target.row
        rook = board.get(Position(row, 7))
        board.set(Position(row, 7), None)
        board.set(Position(row, 5), rook)
        _log.debug("Castling applied: kingside rook relocated on row %d", row)

    elif move.kind is MoveKind.CASTLE_QUEENSIDE:
        # Move rook from a-file to d-file on the same rank.
        row = move.target.row
        rook = board.get(Position(row, 0))
        board.set(Position(row, 0), None)
        board.set(Position(row, 3), rook)
        _log.debug("Castling applied: queenside rook relocated on row %d", row)


def leaves_king_in_check(board: Board, move: Move) -> bool:
    simulated = board.clone()
    apply_move(simulated, move)
    return is_in_check(simulated, move.piece.color)


def generate_legal_moves(board: Board, color: Color, state: "GameState") -> list[Move]:
    return [
        m
        for m in generate_pseudo_legal_moves(board, color, state)
        if not leaves_king_in_check(board, m)
    ]
