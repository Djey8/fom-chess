from chess.application.game import Game
from chess.application.notation import parse_move
from chess.presentation.console import ConsoleUI, format_history, render_board


def test_render_board_contains_files_and_ranks():
    g = Game()
    text = render_board(g.board, colored=False)
    assert "A B C D E F G H" in text
    for r in "12345678":
        assert r in text


def test_console_ui_plays_a_full_short_game():
    moves = iter(["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7", "quit"])
    outputs: list[str] = []

    def fake_input(prompt: str) -> str:
        return next(moves)

    ui = ConsoleUI(input_fn=fake_input, output_fn=outputs.append, colored=False)
    ui.run()

    joined = "\n".join(outputs)
    assert "Checkmate" in joined


# --- format_history unit tests ---

def test_format_history_empty():
    assert format_history([]) == "(no moves yet)"


def test_format_history_even_number_of_moves():
    g = Game()
    for san in ["e4", "e5"]:
        move = parse_move(san, g)
        g.make_move(move)
    result = format_history(g.state.history)
    assert " 1. e2e4  e7e5" in result


def test_format_history_odd_number_of_moves():
    g = Game()
    for san in ["e4", "e5", "Nf3"]:
        move = parse_move(san, g)
        g.make_move(move)
    result = format_history(g.state.history)
    lines = result.splitlines()
    assert len(lines) == 2
    assert " 1. e2e4  e7e5" in lines[0]
    assert " 2. g1f3" in lines[1]
    # Trailing white-only line should not have a black move
    assert lines[1].count("  ") == 0 or not lines[1].strip().endswith("  ")


# --- ConsoleUI integration tests ---

def test_console_ui_help_includes_history():
    inputs = iter(["help", "quit"])
    outputs: list[str] = []

    ui = ConsoleUI(input_fn=lambda _: next(inputs), output_fn=outputs.append, colored=False)
    ui.run()

    joined = "\n".join(outputs)
    assert "history" in joined


def test_console_ui_history_command_no_moves():
    inputs = iter(["history", "quit"])
    outputs: list[str] = []

    ui = ConsoleUI(input_fn=lambda _: next(inputs), output_fn=outputs.append, colored=False)
    ui.run()

    assert "(no moves yet)" in outputs


def test_console_ui_history_command_after_moves():
    inputs = iter(["e4", "e5", "Nf3", "history", "quit"])
    outputs: list[str] = []

    ui = ConsoleUI(input_fn=lambda _: next(inputs), output_fn=outputs.append, colored=False)
    ui.run()

    joined = "\n".join(outputs)
    assert "e2e4" in joined
    assert "e7e5" in joined
    assert "g1f3" in joined
