from itertools import cycle

from _pytest.runner import CollectReport

from xdist.remote import Producer
from xdist.workermanage import parse_spec_config
from xdist.report import report_collection_diff

class LoadFileExclusiveScheduling:
    def __init__(self, config, log=None):
        self.numnodes = len(parse_spec_config(config))
        self.node2collection = {}
        self.node2pending = {}
        self.pending = []
        self.collection = None
        self.exclusive_tests = self.load_exclusive_tests()
        if log is None:
            self.log = Producer("loadsched")
        else:
            self.log = log.loadsched
        self.config = config
        self.maxschedchunk = self.config.getoption("maxschedchunk")

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
            return []

    @property
    def nodes(self):
        """A list of all nodes in the scheduler."""
        return list(self.node2pending.keys())

    @property
    def collection_is_completed(self):
        """Boolean indication initial test collection is complete.

        This is a boolean indicating all initial participating nodes
        have finished collection.  The required number of initial
        nodes is defined by ``.numnodes``.
        """
        return len(self.node2collection) >= self.numnodes

    @property
    def tests_finished(self):
        """Return True if all tests have been executed by the nodes."""
        if not self.collection_is_completed:
            return False
        if self.pending:
            return False
        for pending in self.node2pending.values():
            if len(pending) >= 2:
                return False
        return True

    @property
    def has_pending(self):
        """Return True if there are pending test items

        This indicates that collection has finished and nodes are
        still processing test items, so this can be thought of as
        "the scheduler is active".
        """
        if self.pending:
            return True
        for pending in self.node2pending.values():
            if pending:
                return True
        return False

    def add_node(self, node):
        """Add a new node to the scheduler.

        From now on the node will be allocated chunks of tests to
        execute.

        Called by the ``DSession.worker_workerready`` hook when it
        successfully bootstraps a new node.
        """
        assert node not in self.node2pending
        self.node2pending[node] = []

    def add_node_collection(self, node, collection):
        """Add the collected test items from a node

        The collection is stored in the ``.node2collection`` map.
        Called by the ``DSession.worker_collectionfinish`` hook.
        """
        assert node in self.node2pending
        if self.collection_is_completed:
            # A new node has been added later, perhaps an original one died.
            # .schedule() should have
            # been called by now
            assert self.collection
            if collection != self.collection:
                other_node = next(iter(self.node2collection.keys()))
                msg = report_collection_diff(
                    self.collection, collection, other_node.gateway.id, node.gateway.id
                )
                self.log(msg)
                return
        self.node2collection[node] = list(collection)

    def mark_test_complete(self, node, item_index, duration=0):
        """Mark test item as completed by node

        The duration it took to execute the item is used as a hint to
        the scheduler.

        This is called by the ``DSession.worker_testreport`` hook.
        """
        self.node2pending[node].remove(item_index)
        self.check_schedule(node, duration=duration)

    def mark_test_pending(self, item):
        self.pending.insert(
            0,
            self.collection.index(item),
        )
        for node in self.node2pending:
            self.check_schedule(node)

    def check_schedule(self, node, duration=0):
        """Maybe schedule new items on the node

        If there are any globally pending nodes left then this will
        check if the given node should be given any more tests.  The
        ``duration`` of the last test is optionally used as a
        heuristic to influence how many tests the node is assigned.
        """
        if node.shutting_down:
            return

        if self.pending:
            # how many nodes do we have?
            num_nodes = len(self.node2pending)
            # if our node goes below a heuristic minimum, fill it out to
            # heuristic maximum
            items_per_node_min = max(2, len(self.pending) // num_nodes // 4)
            items_per_node_max = max(2, len(self.pending) // num_nodes // 2)
            node_pending = self.node2pending[node]
            if len(node_pending) < items_per_node_min:
                if duration >= 0.1 and len(node_pending) >= 2:
                    # seems the node is doing long-running tests
                    # and has enough items to continue
                    # so let's rather wait with sending new items
                    return
                num_send = items_per_node_max - len(node_pending)
                # keep at least 2 tests pending even if --maxschedchunk=1
                maxschedchunk = max(2 - len(node_pending), self.maxschedchunk)
                self._send_tests(node, min(num_send, maxschedchunk))
        else:
            node.shutdown()

        self.log("num items waiting for node:", len(self.pending))

    def remove_node(self, node):
        """Remove a node from the scheduler

        This should be called either when the node crashed or at
        shutdown time.  In the former case any pending items assigned
        to the node will be re-scheduled.  Called by the
        ``DSession.worker_workerfinished`` and
        ``DSession.worker_errordown`` hooks.

        Return the item which was being executing while the node
        crashed or None if the node has no more pending items.

        """
        pending = self.node2pending.pop(node)
        if not pending:
            return

        # The node crashed, reassing pending items
        crashitem = self.collection[pending.pop(0)]
        self.pending.extend(pending)
        for node in self.node2pending:
            self.check_schedule(node)
        return crashitem

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

    def _check_nodes_have_same_collection(self):
        """Return True if all nodes have collected the same items.

        If collections differ, this method returns False while logging
        the collection differences and posting collection errors to
        pytest_collectreport hook.
        """
        node_collection_items = list(self.node2collection.items())
        first_node, col = node_collection_items[0]
        same_collection = True
        for node, collection in node_collection_items[1:]:
            msg = report_collection_diff(col, collection, first_node.gateway.id, node.gateway.id)
            if msg:
                same_collection = False
                self.log(msg)
                if self.config is not None:
                    rep = CollectReport(node.gateway.id, "failed", longrepr=msg, result=[])
                    self.config.hook.pytest_collectreport(report=rep)

        return same_collection
