import sys
from datetime import datetime
from itertools import cycle

from _pytest.runner import CollectReport

from xdist.remote import Producer
from xdist.scheduler import LoadScheduling
from xdist.scheduler.loadfile import LoadScopeScheduling
from xdist.workermanage import parse_spec_config
from xdist.report import report_collection_diff


class LoadFileExclusiveScheduling(LoadScopeScheduling):
    def __init__(self, config, log=None):
        super().__init__(config, log)
        self.exclusive_tests = self.load_exclusive_tests()
        self.trace(f"LoadFileExclusiveScheduling have loaded {len(self.exclusive_tests)} exclusive tests.")

    def trace(self, *message: str) -> None:
        """Print a message with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[#]{timestamp}[#] {' '.join(message)}"
        print(full_message, file=sys.stderr)

    @property
    def dedicated_test_nodes(self):
        """Dynamically determine nodes dedicated to running exclusive tests."""
        exclusive_test_count = len(self.exclusive_tests)
        all_nodes = list(self.node2pending.keys())
        # Dedicate the first N nodes to exclusive tests, where N is the number of exclusive tests
        return all_nodes[:exclusive_test_count]

    @property
    def regular_nodes(self):
        """Dynamically determine nodes that are not dedicated to exclusive tests."""
        exclusive_test_count = len(self.exclusive_tests)
        all_nodes = list(self.node2pending.keys())
        assert len(all_nodes) >= exclusive_test_count, f"There are more exclusive tests ({exclusive_test_count}) than nodes ({all_nodes})"
        return all_nodes[exclusive_test_count:]

    def load_exclusive_tests(self, filename="tests/resources/exclusive_tests.txt"):
        try:
            with open(filename, "r") as f:
                return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except FileNotFoundError:
            self.log(f"Exclusive test list '{filename} not found'.")

    def _send_tests(self, node, num):
        tests_for_node = []

        # First, check if the node is dedicated for exclusive tests
        if node in self.dedicated_test_nodes:
            # Attempt to find the first exclusive test for dedicated nodes
            for index, test in enumerate(self.pending):
                if self.collection[test] in self.exclusive_tests:
                    # Schedule the found exclusive test and remove it from pending
                    tests_for_node = [self.pending.pop(index)]
                    self.trace(f"Send exclusive test {self.collection[tests_for_node[0]]} to the node {node.gateway.id}")
                    break  # Exit after scheduling the first found exclusive test
            # If no exclusive tests are pending, and only then, schedule a non-exclusive test
            if not tests_for_node:
                tests_for_node = self.pending[:num]
                del self.pending[:num]
                self.trace(f"Send non-exclusive {len(tests_for_node)} tests to the node {node.gateway.id}")
        else:
            # For non-dedicated nodes, find up to num non-exclusive tests
            non_exclusive_tests = [test for test in self.pending if self.collection[test] not in self.exclusive_tests][:num]
            tests_for_node.extend(non_exclusive_tests)
            for test in non_exclusive_tests:
                self.pending.remove(test)  # Remove the scheduled tests from pending
            self.trace(f"Send non-exclusive {len(non_exclusive_tests)} tests to the node {node.gateway.id}")

        if tests_for_node:
            self.node2pending[node].extend(tests_for_node)
            node.send_runtest_some(tests_for_node)

    def _split_scope(self, nodeid):
        """Group tests by file, except for exclusive tests scheduled on dedicated nodes."""
        return nodeid.split("::", 1)[0]
