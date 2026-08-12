"""Console renderer and input handler — no chess rules here."""

from __future__ import annotations

from typing import Callable

from ..application.game import Game, GameResult, IllegalMoveError
from ..application.notation import NotationError, parse_move
from ..domain.board import Board
from ..domain.color import Color
from ..domain.move import Move
from ..domain.position import Position
from .symbols import empty_square, render_piece

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


def render_board(board: Board, *, colored: bool = True) -> str:
    header = "  A B C D E F G H"
    lines = [header]
    for row in range(8):
        rank = 8 - row
        cells = []
        for col in range(8):
            piece = board.get(Position(row, col))
            cells.append(render_piece(piece, colored=colored) if piece else empty_square())
        lines.append(f"{rank} " + " ".join(cells) + f"  {rank}")
    lines.append(header)
    return "\n".join(lines)


def format_history(moves: list[Move]) -> str:
    """Format the move history as a numbered two-column White/Black list."""
    if not moves:
        return "(no moves yet)"
    lines = []
    for i in range(0, len(moves), 2):
        move_number = i // 2 + 1
        white = f"{moves[i].origin}{moves[i].target}"
        if i + 1 < len(moves):
            black = f"{moves[i + 1].origin}{moves[i + 1].target}"
            lines.append(f"{move_number:2}. {white}  {black}")
        else:
            lines.append(f"{move_number:2}. {white}")
    return "\n".join(lines)


def _result_banner(result: GameResult) -> str:
    return {
        GameResult.WHITE_WINS: "Checkmate — White wins.",
        GameResult.BLACK_WINS: "Checkmate — Black wins.",
        GameResult.STALEMATE: "Stalemate — draw.",
        GameResult.DRAW: "Draw — 50-move rule.",
    }.get(result, "")


class ConsoleUI:
    """Thin console driver for the chess game.

    This class contains zero rule logic; it only renders board state and forwards
    input strings to :func:`parse_move`.
    """

    def __init__(
        self,
        game: Game | None = None,
        *,
        input_fn: InputFn = input,
        output_fn: OutputFn = print,
        colored: bool = True,
    ) -> None:
        self.game = game if game is not None else Game()
        self._input = input_fn
        self._output = output_fn
        self._colored = colored

    def run(self) -> None:
        self._output("Chess MVP — type 'quit' to exit, 'help' for commands.")
        self._output(render_board(self.game.board, colored=self._colored))

        while not self.game.is_over():
            side = "White" if self.game.turn is Color.WHITE else "Black"
            try:
                raw = self._input(f"{side} to move > ").strip()
            except EOFError:
                self._output("")
                return

            if not raw:
                continue
            cmd = raw.lower()
            if cmd in ("quit", "exit"):
                self._output("Goodbye.")
                return
            if cmd == "help":
                self._print_help()
                continue
            if cmd == "board":
                self._output(render_board(self.game.board, colored=self._colored))
                continue
            if cmd == "moves":
                moves = [f"{m.origin}{m.target}" for m in self.game.legal_moves()]
                self._output(" ".join(moves) if moves else "(no legal moves)")
                continue
            if cmd == "history":
                self._output(format_history(self.game.state.history))
                continue
            if cmd == "resign":
                winner = "Black" if self.game.turn is Color.WHITE else "White"
                self._output(f"{side} resigns. {winner} wins.")
                return

            try:
                move = parse_move(raw, self.game)
                outcome = self.game.make_move(move)
            except (NotationError, IllegalMoveError) as exc:
                self._output(f"Illegal move: {exc}")
                continue

            self._output(render_board(self.game.board, colored=self._colored))
            if outcome.result is GameResult.ONGOING:
                if outcome.gave_check:
                    self._output("Check!")
            else:
                banner = _result_banner(outcome.result)
                if outcome.result is GameResult.DRAW and self.game.draw_reason == "threefold":
                    banner = "Draw — threefold repetition."
                self._output(banner)

    def _print_help(self) -> None:
        self._output(
            "\n".join(
                [
                    "Commands:",
                    "  <move>    Play a move. Accepts SAN (e.g. e4, Nf3, exd5, O-O, e8=Q)",
                    "            or coordinate form (e.g. e2e4, e7e8q).",
                    "  board     Re-render the board.",
                    "  moves     List legal moves in coordinate form.",
                    "  history   Show the move list played so far.",
                    "  resign    Resign the game.",
                    "  quit      Exit.",
                ]
            )
        )
