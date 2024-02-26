from collections import OrderedDict

import pytest
from unittest.mock import MagicMock, patch, Mock
from xdist_scheduling_exclusive.exclusive_loadscope_scheduling import ExclusiveLoadScopeScheduling

@pytest.fixture
def mock_exclusive_load_scope_scheduling():
    # Patch the __init__ method of the LoadScopeScheduling parent class to prevent it from running
    with patch('xdist.scheduler.loadfile.LoadScopeScheduling.__init__', return_value=None):
        # Patch the load_exclusive_tests function to return a mock set of exclusive tests
        with patch('xdist_scheduling_exclusive.load_exclusive_tests.load_exclusive_tests', return_value={"test_exclusive_1", "test_exclusive_2"}):
            exclusive_load_scope_scheduling = ExclusiveLoadScopeScheduling(Mock(), Mock())
            exclusive_load_scope_scheduling.workqueue = MagicMock()
            exclusive_load_scope_scheduling.assigned_work = MagicMock()
            exclusive_load_scope_scheduling.registered_collections = MagicMock()
            exclusive_load_scope_scheduling.exclusive_tests_scheduled = set()
            exclusive_load_scope_scheduling.workqueue = OrderedDict([
                ("mock_scope", {
                    "test_mock_exclusive.py::test_exclusive_1": False,
                    "test_mock_exclusive.py::test_non_exclusive_1": False
                }),
                ("another_scope", {
                    "test_mock_exclusive.py::test_exclusive_2": False
                })
            ])
            return exclusive_load_scope_scheduling


def test_exclusive_test_scheduling(mock_exclusive_load_scope_scheduling):
    # Mock the node and work unit as needed for your test scenario
    mock_node = MagicMock()
    mock_work_unit = {"test_mock_exclusive.py::test_exclusive_1": False}
    mock_exclusive_load_scope_scheduling._send_work_to_node = MagicMock()

    mock_exclusive_load_scope_scheduling.workqueue.update({
        "mock_scope": mock_work_unit
    })

    mock_exclusive_load_scope_scheduling._assign_work_unit(mock_node)

    # todo: asserts