"""pytest-xdist LoadFileScheduling descendant that place exclusive tests to separate group."""

from typing import Any, Optional

from xdist.scheduler.loadfile import LoadFileScheduling

from xdist_scheduling_exclusive.scheduler_base import load_exclusive_tests, trace

EXCLUSIVE_TEST_SCOPE_PREFIX = "-exclusive-test-"


class ExclusiveLoadFileScheduling(LoadFileScheduling):  # type: ignore  # pylint: disable=abstract-method
    """Custom xdist scheduling.

    Place tests from exclusive_tests.txt to unique test groups.
    Other tests are grouped as in `--dist loadfile`: tests from the same file run on the same node.
    """

    def __init__(
        self,
        config: Any,
        log: Optional[Any] = None,
        exclusive_tests: Optional[list[str]] = None,
    ) -> None:
        """Load tests from exclusive_tests.txt."""
        super().__init__(config, log)
        self.exclusive_tests = exclusive_tests or load_exclusive_tests()
        trace(
            f"ExclusiveLoadFileScheduling have loaded {len(self.exclusive_tests)} exclusive tests.",
        )

    def _split_scope(self, nodeid: str) -> str:
        """Determine the scope (grouping) of a nodeid, exclusive tests in unique scopes."""
        if nodeid in self.exclusive_tests:
            # Treat each exclusive test as a unique scope to force it to run on a separate node
            return f"{EXCLUSIVE_TEST_SCOPE_PREFIX}::{nodeid}"
        # Fall back to the parent class's behavior for non-exclusive tests
        return super()._split_scope(nodeid)  # type: ignore
