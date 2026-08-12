"""Board: 8x8 grid holding pieces. No rules, just storage + helpers."""

from __future__ import annotations

from typing import Iterator, Optional

from .color import Color
from .piece import Piece, PieceType
from .position import Position


class Board:
    """Mutable 8x8 grid. Row 0 is rank 8, row 7 is rank 1."""

    def __init__(self) -> None:
        self._grid: list[list[Optional[Piece]]] = [[None] * 8 for _ in range(8)]

    # ---- construction -------------------------------------------------
    @classmethod
    def empty(cls) -> "Board":
        return cls()

    @classmethod
    def standard(cls) -> "Board":
        """Standard chess starting position."""
        board = cls()
        back_rank = [
            PieceType.ROOK,
            PieceType.KNIGHT,
            PieceType.BISHOP,
            PieceType.QUEEN,
            PieceType.KING,
            PieceType.BISHOP,
            PieceType.KNIGHT,
            PieceType.ROOK,
        ]
        for col, pt in enumerate(back_rank):
            board._grid[0][col] = Piece(pt, Color.BLACK)
            board._grid[1][col] = Piece(PieceType.PAWN, Color.BLACK)
            board._grid[6][col] = Piece(PieceType.PAWN, Color.WHITE)
            board._grid[7][col] = Piece(pt, Color.WHITE)
        return board

    def clone(self) -> "Board":
        new = Board()
        new._grid = [row[:] for row in self._grid]
        return new

    # ---- access -------------------------------------------------------
    def get(self, pos: Position) -> Optional[Piece]:
        return self._grid[pos.row][pos.col]

    def set(self, pos: Position, piece: Optional[Piece]) -> None:
        self._grid[pos.row][pos.col] = piece

    def is_empty(self, pos: Position) -> bool:
        return self._grid[pos.row][pos.col] is None

    def iter_pieces(self) -> Iterator[tuple[Position, Piece]]:
        for r in range(8):
            for c in range(8):
                piece = self._grid[r][c]
                if piece is not None:
                    yield Position(r, c), piece

    def find_king(self, color: Color) -> Optional[Position]:
        for pos, piece in self.iter_pieces():
            if piece.type is PieceType.KING and piece.color is color:
                return pos
        return None

    def position_key(self) -> tuple:
        """Return a hashable fingerprint of the current piece placement.

        The key is a sorted tuple of ``(row, col, piece_type_value,
        piece_color_value)`` entries so that two boards with identical piece
        placement produce the same key regardless of the order in which pieces
        were placed.
        """
        return tuple(
            sorted(
                (pos.row, pos.col, piece.type.value, piece.color.value)
                for pos, piece in self.iter_pieces()
            )
        )
