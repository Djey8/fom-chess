"""Notation parsing/formatting.

Supports:
    * Simple coordinate notation: ``e2e4``, ``e7e8q`` (promotion piece letter).
    * Castling: ``O-O`` (kingside), ``O-O-O`` (queenside). ``0-0`` / ``0-0-0`` also accepted.
    * Standard SAN (subset sufficient for MVP):
        - Pawn moves: ``e4``, ``exd5``, ``e8=Q``, ``exd8=Q``.
        - Piece moves: ``Nf3``, ``Nbd2``, ``R1e2``, ``Qh4xe1``, ``Bxe5``.
        - Trailing ``+`` (check) and ``#`` (mate) are tolerated.
"""

from __future__ import annotations

import re
from typing import Optional

from ..domain.color import Color
from ..domain.move import Move, MoveKind
from ..domain.piece import PieceType
from ..domain.position import FILES, RANKS, Position
from .game import Game


PIECE_LETTERS = {"K", "Q", "R", "B", "N"}
PROMOTION_LETTERS = {"Q": PieceType.QUEEN, "R": PieceType.ROOK, "B": PieceType.BISHOP, "N": PieceType.KNIGHT}


class NotationError(ValueError):
    """Raised when the input cannot be parsed as a chess move in the given position."""


# Regex for SAN piece or pawn move
_SAN_RE = re.compile(
    r"""^
    (?P<piece>[KQRBN])?
    (?P<from_file>[a-h])?
    (?P<from_rank>[1-8])?
    (?P<capture>x)?
    (?P<to>[a-h][1-8])
    (?:=(?P<promotion>[QRBN]))?
    (?P<checkmark>[+#])?
    $""",
    re.VERBOSE,
)


def parse_move(text: str, game: Game) -> Move:
    """Parse ``text`` into a legal :class:`Move` in the current ``game``.

    Raises :class:`NotationError` if the string cannot be mapped to a unique legal move.
    """
    raw = text.strip()
    if not raw:
        raise NotationError("Empty move.")

    normalized = raw.replace("0", "O")

    # Castling
    if normalized in ("O-O", "O-O+", "O-O#"):
        return _find_castle(game, kingside=True)
    if normalized in ("O-O-O", "O-O-O+", "O-O-O#"):
        return _find_castle(game, kingside=False)

    # Coordinate form: e2e4, e7e8q
    coord = _try_coordinate(raw, game)
    if coord is not None:
        return coord

    # SAN
    m = _SAN_RE.match(raw)
    if m is None:
        raise NotationError(f"Cannot parse move: {raw!r}")

    piece_letter = m.group("piece") or "P"
    piece_type = PieceType(piece_letter)
    from_file = m.group("from_file")
    from_rank = m.group("from_rank")
    target = Position.from_algebraic(m.group("to"))
    promotion = (
        PROMOTION_LETTERS[m.group("promotion")] if m.group("promotion") else None
    )

    legal = game.legal_moves()
    candidates = []
    for mv in legal:
        if mv.piece.type is not piece_type:
            continue
        if mv.target != target:
            continue
        if promotion is not None and mv.promotion is not promotion:
            continue
        if promotion is None and piece_type is PieceType.PAWN and mv.is_promotion:
            # Require explicit promotion letter for pawn promotions.
            continue
        if from_file is not None and mv.origin.file != from_file:
            continue
        if from_rank is not None and mv.origin.rank != from_rank:
            continue
        # Pawn captures in SAN always name the originating file.
        if piece_type is PieceType.PAWN and mv.is_capture and from_file is None:
            continue
        candidates.append(mv)

    if not candidates:
        raise NotationError(f"No legal move matches {raw!r}.")
    if len(candidates) > 1:
        raise NotationError(
            f"Ambiguous move {raw!r}: {len(candidates)} candidates."
        )
    return candidates[0]


def _find_castle(game: Game, kingside: bool) -> Move:
    kind = MoveKind.CASTLE_KINGSIDE if kingside else MoveKind.CASTLE_QUEENSIDE
    for mv in game.legal_moves():
        if mv.kind is kind:
            return mv
    raise NotationError("Castling is not legal in this position.")


def _try_coordinate(text: str, game: Game) -> Optional[Move]:
    s = text.strip().lower().replace("-", "")
    if len(s) not in (4, 5):
        return None
    if s[0] not in FILES or s[1] not in RANKS or s[2] not in FILES or s[3] not in RANKS:
        return None
    origin = Position.from_algebraic(s[:2])
    target = Position.from_algebraic(s[2:4])
    promotion: Optional[PieceType] = None
    if len(s) == 5:
        letter = s[4].upper()
        if letter not in PROMOTION_LETTERS:
            return None
        promotion = PROMOTION_LETTERS[letter]

    candidates = [
        m
        for m in game.legal_moves()
        if m.origin == origin and m.target == target and m.promotion == promotion
    ]
    if not candidates:
        # If promotion not given but required, surface a clearer error.
        maybe_promo = [m for m in game.legal_moves() if m.origin == origin and m.target == target]
        if maybe_promo and any(m.is_promotion for m in maybe_promo) and promotion is None:
            raise NotationError(
                "Promotion required: append Q/R/B/N (e.g. e7e8q)."
            )
        return None
    if len(candidates) > 1:
        raise NotationError("Ambiguous coordinate move.")
    return candidates[0]


def format_move(move: Move) -> str:
    """Format a move in SAN-ish form (sufficient for display)."""
    if move.kind is MoveKind.CASTLE_KINGSIDE:
        return "O-O"
    if move.kind is MoveKind.CASTLE_QUEENSIDE:
        return "O-O-O"

    piece_letter = "" if move.piece.type is PieceType.PAWN else move.piece.type.value
    capture = "x" if move.is_capture else ""
    target = move.target.algebraic
    promo = f"={move.promotion.value}" if move.promotion else ""

    if move.piece.type is PieceType.PAWN:
        if move.is_capture:
            return f"{move.origin.file}{capture}{target}{promo}"
        return f"{target}{promo}"

    return f"{piece_letter}{capture}{target}"
