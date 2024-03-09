"""Load tests from exclusive_tests.txt."""

import sys
from datetime import datetime


def load_exclusive_tests(file_name: str = "tests/resources/exclusive_tests.txt") -> list[str]:
    """Load tests from exclusive_tests.txt."""
    try:
        with open(file_name, "r", encoding="utf8") as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    except FileNotFoundError as e:
        raise ValueError(f"Exclusive tests list '{file_name}' not found.") from e


def trace(*message: str) -> None:
    """Print a message with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"(@){timestamp}(@) {' '.join(message)}"
    print(full_message, file=sys.stderr)
