"""pytest-xdist scheduler that runs exclusive tests on dedicated workers."""
import sys
from datetime import datetime
from typing import Any, List

from xdist.dsession import LoadScheduling
from xdist.workermanage import WorkerController

from xdist_scheduling_exclusive.load_exclusive_tests import load_exclusive_tests


class ExclusiveLoadScheduling(LoadScheduling):  # type: ignore
    """Custom xdist scheduling.

    Run tests from exclusive_tests.txt on separate xdist nodes.
    """

    _exclusive_tests_indices: List[int]

    def __init__(self, config: Any, log: Any) -> None:
        """Load tests from exclusive_tests.txt."""
        super().__init__(config, log)
        self.exclusive_tests = load_exclusive_tests()
        self.trace(f"ExclusiveScheduling have loaded {len(self.exclusive_tests)} exclusive tests.")

    def trace(self, *message: str) -> None:
        """Print a message with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[#]{timestamp}[#] {' '.join(message)}"
        print(full_message, file=sys.stderr)

    @property
    def exclusive_tests_indices(self) -> list[int]:
        """Map exclusive test names to indices.

        At __init__ tests are not collected so we do lazy initialization.
        Calculate at first access and use cache afterward.
        """
        if not hasattr(self, "_exclusive_tests_indices"):
            self._exclusive_tests_indices = [
                self.collection.index(
                    name
                )  # we could create reverse-index but not worth it - less than 100 tests
                for name in self.exclusive_tests
                if name in self.collection
            ]
        return self._exclusive_tests_indices

    def _send_tests(self, node: WorkerController, num: int) -> None:
        tests_to_send = []
        exclusive_sent = False

        # Attempt to send exclusive tests first
        for exclusive_test in self.exclusive_tests_indices[:]:  # Copy list for safe iteration
            if exclusive_test in self.pending:
                self.trace(
                    f"Send exclusive test {self.collection[exclusive_test]} " f"to the node {node.gateway.id}"
                )
                self.pending.remove(exclusive_test)
                tests_to_send.append(exclusive_test)
                self.exclusive_tests_indices.remove(exclusive_test)  # Remove sent test
                exclusive_sent = True
                break  # Ensure only one exclusive test is sent per call

        if not exclusive_sent:
            # If no exclusive test was sent, fill in with regular pending tests
            for test in self.pending[:]:  # Copy list for safe iteration
                if len(tests_to_send) < num:
                    if test not in self.exclusive_tests_indices:
                        self.trace(
                            f"Send non-exclusive test {self.collection[test]} "
                            f"to the node {node.gateway.id}"
                        )
                        tests_to_send.append(test)
                        self.pending.remove(test)
                else:
                    break  # Stop if we have enough tests to send

        # Send the collected tests to the node
        if tests_to_send:
            self.node2pending[node].extend(tests_to_send)
            node.send_runtest_some(tests_to_send)
