"""Load tests from exclusive_tests.txt."""


def load_exclusive_tests(filename: str = "tests/resources/exclusive_tests.txt") -> list[str]:
    """Load tests from exclusive_tests.txt."""
    try:
        with open(filename, "r", encoding="utf8") as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    except FileNotFoundError as e:
        raise ValueError(f"Exclusive tests list '{filename}' not found.") from e
