"""Entry point: run the console chess game."""

from __future__ import annotations

from .presentation.console import ConsoleUI


def main() -> None:
    ConsoleUI().run()


if __name__ == "__main__":
    main()
