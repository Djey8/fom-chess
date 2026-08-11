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

logger = logging.getLogger(__name__)

from .board import Board
from .color import Color
from .move import Move, MoveKind
from .piece import Piece, PieceType
from .position import Position

if TYPE_CHECKING:
    from .game_state import GameState


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
    """Generate pseudo-legal pawn moves including en passant captures."""
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

    # Diagonal captures (normal + en passant)
    for dcol in (-1, 1):
        target = origin.offset(direction, dcol)
        if target is None:
            continue
        occupant = board.get(target)
        if occupant is not None and occupant.color is not piece.color:
            moves.append(
                Move(piece, origin, target, MoveKind.CAPTURE, captured=occupant)
            )
        elif en_passant_target is not None and target == en_passant_target:
            # The captured pawn sits on the same rank as the capturing pawn.
            captured_pawn_square = origin.offset(0, dcol)
            if captured_pawn_square is not None:
                captured_pawn = board.get(captured_pawn_square)
                if (
                    captured_pawn is not None
                    and captured_pawn.type is PieceType.PAWN
                    and captured_pawn.color is not piece.color
                ):
                    logger.debug(
                        "En passant capture accepted: %s -> %s (captures pawn on %s)",
                        origin.algebraic,
                        target.algebraic,
                        captured_pawn_square.algebraic,
                    )
                    moves.append(
                        Move(
                            piece,
                            origin,
                            target,
                            MoveKind.EN_PASSANT,
                            captured=captured_pawn,
                        )
                    )
                else:
                    logger.debug(
                        "En passant rejected: no valid pawn on %s",
                        captured_pawn_square.algebraic if captured_pawn_square else "None",
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
        # NOTE (thesis baseline `thesis-baseline-2026-08-10`): castling (UC-3)
        # is intentionally not implemented yet — the king only has its normal
        # one-step moves.
        return _step_moves(board, origin, piece, KING_OFFSETS)
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

    Handles en passant capture by removing the captured pawn from its actual
    square (not the target square of the capturing pawn).
    """
    board.set(move.origin, None)
    board.set(move.target, move.piece)
    if move.kind is MoveKind.EN_PASSANT:
        # The captured pawn is on the same rank as the origin, same file as target.
        captured_square = Position(move.origin.row, move.target.col)
        board.set(captured_square, None)


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
