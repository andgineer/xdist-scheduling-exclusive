"""pytest-xdist LoadFileScheduling descendant that place exclusive tests to separate group."""
from datetime import datetime
from typing import Any

from xdist.scheduler.loadfile import LoadFileScheduling

from xdist_scheduling_exclusive.load_exclusive_tests import load_exclusive_tests

EXCLUSIVE_TEST_SCOPE_PREFIX = "-exclusive-test-"


class ExclusiveLoadFileScheduling(LoadFileScheduling):  # type: ignore  # pylint: disable=abstract-method
    """Custom xdist scheduling.

    Place tests from exclusive_tests.txt to unique test groups.
    Other tests are grouped as in `--dist loadfile`: tests from the same file run on the same node.
    """

    def __init__(self, config: Any, log: Any) -> None:
        """Load tests from exclusive_tests.txt."""
        super().__init__(config, log)
        self.exclusive_tests = load_exclusive_tests()
        self.trace(f"ExclusiveLoadFileScheduling have loaded {len(self.exclusive_tests)} exclusive tests.")

    def trace(self, *message: str) -> None:
        """Print a message with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[#]{timestamp}[#] {' '.join(message)}"
        print(full_message)

    def _split_scope(self, nodeid: str) -> str:
        """Determine the scope (grouping) of a nodeid, exclusive tests in unique scopes."""
        if nodeid in self.exclusive_tests:
            # Treat each exclusive test as a unique scope to force it to run on a separate node
            return f"{EXCLUSIVE_TEST_SCOPE_PREFIX}::{nodeid}"
        # Fall back to the parent class's behavior for non-exclusive tests
        return super()._split_scope(nodeid)  # type: ignore
