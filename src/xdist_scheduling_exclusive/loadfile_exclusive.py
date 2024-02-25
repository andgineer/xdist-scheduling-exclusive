from itertools import cycle

from _pytest.runner import CollectReport

from xdist.remote import Producer
from xdist.scheduler import LoadScheduling
from xdist.workermanage import parse_spec_config
from xdist.report import report_collection_diff


class LoadFileExclusiveScheduling(LoadScheduling):
    def __init__(self, config, log=None):
        super().__init__(config, log)
        self.exclusive_tests = self.load_exclusive_tests()

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

    def schedule(self):
        """Initiate distribution of the test collection

        Initiate scheduling of the items across the nodes.  If this
        gets called again later it behaves the same as calling
        ``.check_schedule()`` on all nodes so that newly added nodes
        will start to be used.

        This is called by the ``DSession.worker_collectionfinish`` hook
        if ``.collection_is_completed`` is True.
        """
        assert self.collection_is_completed

        # Initial distribution already happened, reschedule on all nodes
        if self.collection is not None:
            for node in self.nodes:
                self.check_schedule(node)
            return

        # XXX allow nodes to have different collections
        if not self._check_nodes_have_same_collection():
            self.log("**Different tests collected, aborting run**")
            return

        # Collections are identical, create the index of pending items.
        self.collection = list(self.node2collection.values())[0]
        self.pending[:] = range(len(self.collection))
        if not self.collection:
            return

        if self.maxschedchunk is None:
            self.maxschedchunk = len(self.collection)

        # Custom scheduling for exclusive tests on dedicated nodes
        for node in self.dedicated_test_nodes:
            self._send_tests(node, 1)

        # Adjust pending tests after exclusive tests have been scheduled
        if len(self.pending) < 2 * len(self.regular_nodes):
            nodes = cycle(self.regular_nodes)
            for i in range(len(self.pending)):
                self._send_tests(next(nodes), 1)
        else:
            # Send batches of consecutive tests. By default, pytest sorts tests
            # in order for optimal single-threaded execution, minimizing the
            # number of necessary fixture setup/teardown. Try to keep that
            # optimal order for every worker.

            # how many items per node do we have about?
            items_per_node = len(self.collection) // len(self.node2pending)
            # take a fraction of tests for initial distribution
            node_chunksize = min(items_per_node // 4, self.maxschedchunk)
            node_chunksize = max(node_chunksize, 2)
            # and initialize each node with a chunk of tests
            for node in self.nodes:
                self._send_tests(node, node_chunksize)

        if not self.pending:
            # initial distribution sent all tests, start node shutdown
            for node in self.nodes:
                node.shutdown()

    def _send_tests(self, node, num):
        tests_for_node = []

        # First, check if the node is dedicated for exclusive tests
        if node in self.dedicated_test_nodes:
            # Attempt to find the first exclusive test for dedicated nodes
            for index, test in enumerate(self.pending):
                if self.collection[test] in self.exclusive_tests:
                    # Schedule the found exclusive test and remove it from pending
                    tests_for_node = [self.pending.pop(index)]
                    break  # Exit after scheduling the first found exclusive test
            # If no exclusive tests are pending, and only then, schedule a non-exclusive test
            if not tests_for_node:
                tests_for_node = self.pending[:num]
                del self.pending[:num]
        else:
            # For non-dedicated nodes, find up to num non-exclusive tests
            non_exclusive_tests = [test for test in self.pending if self.collection[test] not in self.exclusive_tests][:num]
            tests_for_node.extend(non_exclusive_tests)
            for test in non_exclusive_tests:
                self.pending.remove(test)  # Remove the scheduled tests from pending

        if tests_for_node:
            self.node2pending[node].extend(tests_for_node)
            node.send_runtest_some(tests_for_node)
