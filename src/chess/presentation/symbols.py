"""Unicode + ANSI symbols for rendering pieces on the console."""

from __future__ import annotations

import sys

from ..domain.color import Color
from ..domain.piece import Piece, PieceType

RESET = "\033[0m"
WHITE_ANSI = "\033[97m"
BLACK_ANSI = "\033[30m"

_UNICODE = {
    PieceType.KING: "\u265A",
    PieceType.QUEEN: "\u265B",
    PieceType.ROOK: "\u265C",
    PieceType.BISHOP: "\u265D",
    PieceType.KNIGHT: "\u265E",
    PieceType.PAWN: "\u265F",
}


def _stdout_supports_unicode() -> bool:
    enc = getattr(sys.stdout, "encoding", None) or ""
    try:
        "\u265A".encode(enc)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


USE_UNICODE = _stdout_supports_unicode()


def render_piece(piece: Piece, *, colored: bool = True) -> str:
    if USE_UNICODE:
        glyph = _UNICODE[piece.type]
    else:
        letter = piece.type.value
        glyph = letter if piece.color is Color.WHITE else letter.lower()
    if not colored:
        return glyph
    ansi = WHITE_ANSI if piece.color is Color.WHITE else BLACK_ANSI
    return f"{ansi}{glyph}{RESET}"


def empty_square() -> str:
    return "."
