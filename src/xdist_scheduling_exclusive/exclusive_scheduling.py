"""pytest-xdist scheduler that runs some tests on dedicated workers.

Can significantly improve runtime by running long tests on separate workers.
"""
from datetime import datetime
from typing import Any, List

from xdist.dsession import LoadScheduling
from xdist.workermanage import WorkerController


class ExclusiveScheduling(LoadScheduling):  # type: ignore
    """Custom xdist scheduling.

    Run tests from exclusive_tests.txt on separate xdist nodes."""

    _exclusive_tests_indices: List[int]

    def __init__(self, config: Any, log: Any) -> None:
        """Load tests from exclusive_tests.txt."""
        super().__init__(config, log)
        self.exclusive_tests = self.load_exclusive_tests()
        self.trace(f"ExclusiveScheduling have loaded {len(self.exclusive_tests)} exclusive tests.")

    def trace(self, *message: str) -> None:
        """Print a message with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[#]{timestamp}[#] {' '.join(message)}"
        print(full_message)

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
        """Called in LoadScheduling."""
        tests_to_send = []
        tests_to_send_num = num

        # Send one exclusive test if available
        for i, test in enumerate(self.exclusive_tests_indices):
            if test in self.pending:
                self.trace(
                    f"Send exclusive test {self.collection[test]} to the node {node.gateway.id}"
                )
                self.pending.remove(test)
                tests_to_send.append(test)
                del self.exclusive_tests_indices[
                    i
                ]  # Remove the exclusive test we sent from the list
                tests_to_send_num -= 1
                break  # Only send one exclusive test

        if not tests_to_send:
            # Fill in with regular pending tests, excluding any that are exclusive
            for test in self.pending[:]:  # Iterate over a shallow copy to allow modification
                if tests_to_send_num == 0:
                    break  # Stop early if we have enough tests
                if test not in self.exclusive_tests_indices:
                    self.trace(
                        f"Send non-exclusive test {self.collection[test]} "
                        f"to the node {node.gateway.id}"
                    )
                    tests_to_send.append(test)
                    self.pending.remove(test)  # Now safe to modify the original list
                    tests_to_send_num -= 1

            # If we do not have enough non-exclusive tests, send from the head of the pending tests
            fallback_tests = self.pending[:tests_to_send_num]
            if fallback_tests:
                self.trace(
                    f"FAIL to isolate {len(fallback_tests)} exclusive test(s), "
                    f"send them to the node {node.gateway.id}"
                )
                del self.pending[:tests_to_send_num]
                tests_to_send.extend(fallback_tests)

        # Send the collected tests to the node
        if tests_to_send:
            self.node2pending[node].extend(tests_to_send)
            node.send_runtest_some(tests_to_send)

    def load_exclusive_tests(
        self, filename: str = "tests/resources/exclusive_tests.txt"
    ) -> list[str]:
        """Load tests from exclusive_tests.txt."""
        try:
            with open(filename, "r", encoding="utf8") as f:
                return [
                    line.strip() for line in f if line.strip() and not line.strip().startswith("#")
                ]
        except FileNotFoundError:
            self.trace(f"Exclusive tests list '{filename}' not found.")
            return []
