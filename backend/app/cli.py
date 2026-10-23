"""Служебные команды: python -m app.cli <команда>."""
import sys


def bootstrap() -> None:
    """Начальные данные, без которых система не работает. Идемпотентно."""


COMMANDS = {"bootstrap": bootstrap}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit(f"usage: python -m app.cli [{'|'.join(COMMANDS)}]")
    COMMANDS[sys.argv[1]]()
