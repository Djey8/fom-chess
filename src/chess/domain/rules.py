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


def _castling_moves(
    board: Board, origin: Position, piece: Piece, state: "GameState"
) -> list[Move]:
    """Generate castling pseudo-legal moves for the king at *origin*.

    Validates:
    * Castling right is still active.
    * All squares between king and rook are empty.
    * King is not currently in check.
    * King does not pass through or land on an attacked square.
    """
    moves: list[Move] = []
    color = piece.color
    rights = state.castling_rights(color)
    opponent = color.opponent
    king_row = origin.row

    # King must be on its starting square
    king_start_col = 4
    if origin.col != king_start_col:
        _log.debug("Castling rejected: king not on starting square for %s", color)
        return moves

    # King must not be in check
    if is_square_attacked(board, origin, opponent):
        _log.debug("Castling rejected: %s king is in check", color)
        return moves

    def _try_castle(
        kingside: bool,
        rook_col: int,
        king_target_col: int,
        between_cols: list[int],
        pass_through_cols: list[int],
        kind: MoveKind,
    ) -> None:
        right = rights.kingside if kingside else rights.queenside
        side = "kingside" if kingside else "queenside"
        if not right:
            _log.debug("Castling rejected: %s %s right revoked", color, side)
            return
        # Rook must be present
        rook_pos = Position(king_row, rook_col)
        rook = board.get(rook_pos)
        if rook is None or rook.type is not PieceType.ROOK or rook.color is not color:
            _log.debug("Castling rejected: %s %s rook missing", color, side)
            return
        # All squares between king and rook must be empty
        for col in between_cols:
            if not board.is_empty(Position(king_row, col)):
                _log.debug(
                    "Castling rejected: %s %s path blocked at col %d", color, side, col
                )
                return
        # King must not pass through or land on an attacked square
        for col in pass_through_cols:
            sq = Position(king_row, col)
            if is_square_attacked(board, sq, opponent):
                _log.debug(
                    "Castling rejected: %s %s square col %d is attacked", color, side, col
                )
                return
        king_target = Position(king_row, king_target_col)
        _log.debug("Castling accepted: %s %s", color, side)
        moves.append(Move(piece, origin, king_target, kind))

    # Kingside: king e->g, rook h->f; between: f,g; pass-through: f,g
    _try_castle(
        kingside=True,
        rook_col=7,
        king_target_col=6,
        between_cols=[5, 6],
        pass_through_cols=[5, 6],
        kind=MoveKind.CASTLE_KINGSIDE,
    )
    # Queenside: king e->c, rook a->d; between: b,c,d; pass-through: c,d
    _try_castle(
        kingside=False,
        rook_col=0,
        king_target_col=2,
        between_cols=[1, 2, 3],
        pass_through_cols=[3, 2],
        kind=MoveKind.CASTLE_QUEENSIDE,
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
    """Mutate ``board`` by applying ``move``. Handles castling rook relocation."""
    board.set(move.origin, None)
    board.set(move.target, move.piece)
    if move.kind is MoveKind.CASTLE_KINGSIDE:
        row = move.origin.row
        rook = board.get(Position(row, 7))
        board.set(Position(row, 7), None)
        board.set(Position(row, 5), rook)
    elif move.kind is MoveKind.CASTLE_QUEENSIDE:
        row = move.origin.row
        rook = board.get(Position(row, 0))
        board.set(Position(row, 0), None)
        board.set(Position(row, 3), rook)


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
