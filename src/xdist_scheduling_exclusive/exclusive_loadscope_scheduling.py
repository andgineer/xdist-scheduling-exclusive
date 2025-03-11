"""pytest-xdist LoadScopeScheduling descendant that schedule exclusive tests to dedicated nodes."""

from typing import Any, Optional

from xdist.scheduler.loadfile import LoadScopeScheduling

from xdist_scheduling_exclusive.scheduler_base import load_exclusive_tests, trace

EXCLUSIVE_TEST_SCOPE_PREFIX = "-exclusive-test-"


class ExclusiveLoadScopeScheduling(LoadScopeScheduling):  # type: ignore  # pylint: disable=abstract-method
    """Custom xdist scheduling.

    Schedule tests from exclusive_tests.txt first and on dedicated nodes.
    Other tests are grouped as in `--dist loadfile`: tests from the same file run on the same node.
    """

    def __init__(
        self,
        config: Any,
        log: Optional[Any] = None,
        exclusive_tests: Optional[list[str]] = None,
        dedicate_nodes: bool = False,
    ) -> None:
        """Load tests from exclusive_tests.txt.

        If dedicate_nodes is True, exclusive tests exclusively occupy their nodes.
        """
        super().__init__(config, log)
        self.exclusive_tests = exclusive_tests or load_exclusive_tests()
        self.dedicate_nodes = dedicate_nodes
        self.exclusive_tests_nodes: set[str] = set()
        self.exclusive_tests_scheduled: set[str] = set()

        trace(
            f"LoadFileExclusiveScheduling have loaded {len(self.exclusive_tests)} exclusive tests.",
        )
        self.dedicated_nodes_assigned = False

    @property
    def collection_is_completed(self) -> bool:
        """Verify we have enough nodes for dedicated exclusive tests run."""
        result = super().collection_is_completed
        if result:
            assert not self.dedicate_nodes or len(self.exclusive_tests_nodes) < self.numnodes, (
                f"Not enough nodes ({self.numnodes}) to dedicate "
                f"to exclusive tests ({len(self.exclusive_tests_nodes)})"
            )
        return result  # type: ignore

    def _assign_work_unit(self, node: Any) -> None:
        if set(self.exclusive_tests) - self.exclusive_tests_scheduled:
            for scope, work_unit in self.workqueue.items():
                # Find if any test in the current scope is exclusive and unscheduled
                exclusive_test_in_scope = any(test in self.exclusive_tests for test in work_unit)
                if exclusive_test_in_scope:
                    # Schedule the exclusive test
                    self._schedule_exclusive_test(node, scope, work_unit)
                    return  # Exit after scheduling an exclusive test to ensure prioritization

        if not self.dedicate_nodes or node.gateway.id not in self.exclusive_tests_nodes:
            super()._assign_work_unit(node)

    def _schedule_exclusive_test(self, node: Any, scope: str, work_unit: Any) -> None:
        self.exclusive_tests_nodes.add(node.gateway.id)
        self.exclusive_tests_scheduled.update(work_unit.keys())
        self.workqueue.pop(scope)
        self.assigned_work[node][scope] = work_unit
        self._send_work_to_node(node, work_unit)

    def _send_work_to_node(self, node: Any, work_unit: Any) -> None:
        """Send work to the node.

        The work_unit is a dictionary where the keys are test identifiers.
        This method converts those identifiers into the format expected by the node
        and then dispatches the work.
        """
        test_identifiers = list(work_unit.keys())

        node_test_collection = self.registered_collections[node]
        test_indices = [
            node_test_collection.index(test_id)
            for test_id in test_identifiers
            if test_id in node_test_collection
        ]

        if test_indices:
            node.send_runtest_some(test_indices)
            trace(f"Sent {len(test_indices)} tests to {node} for execution.")
        else:
            trace(f"No matching tests found in node's collection for {node}.")

    def _split_scope(self, nodeid: str) -> str:
        """Group tests by file, except for exclusive tests scheduled on dedicated nodes."""
        if nodeid in self.exclusive_tests:
            # Treat each exclusive test as a unique scope
            return f"{EXCLUSIVE_TEST_SCOPE_PREFIX}::{nodeid}"
        return nodeid.split("::", 1)[0]
