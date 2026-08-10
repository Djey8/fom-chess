"""En passant execution and state-lifecycle tests."""

from chess.application.game import Game
from chess.application.notation import parse_move
from chess.domain.position import Position


def _play(game: Game, *sans: str) -> None:
    """Apply a sequence of SAN/coordinate moves to a game."""
    for san in sans:
        move = parse_move(san, game)
        game.make_move(move)


def test_en_passant_capture_removes_pawn_from_actual_square() -> None:
    """En passant removes the adjacent pawn, not a pawn on the target square."""
    game = Game()

    _play(game, "e4", "a6", "e5", "d5", "exd6")

    assert game.board.is_empty(Position.from_algebraic("d5"))
    assert game.board.get(Position.from_algebraic("d6")) is not None


def test_en_passant_expires_after_one_move() -> None:
    """En passant is unavailable after one full move if not used immediately."""
    game = Game()

    _play(game, "e4", "h5", "e5", "d5")
    assert game.find_legal_move(
        Position.from_algebraic("e5"), Position.from_algebraic("d6")
    ) is not None

    _play(game, "Nc3", "Nf6")

    assert game.state.en_passant_target is None
    assert game.find_legal_move(
        Position.from_algebraic("e5"), Position.from_algebraic("d6")
    ) is None


def test_en_passant_target_is_set_on_double_pawn_and_cleared_next_move() -> None:
    """Game state tracks and clears the en passant target lifecycle correctly."""
    game = Game()

    _play(game, "e4")
    assert game.state.en_passant_target == Position.from_algebraic("e3")

    _play(game, "a6")
    assert game.state.en_passant_target is None
