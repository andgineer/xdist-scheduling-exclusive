import pytest
from unittest.mock import Mock, patch

from xdist_scheduling_exclusive.exclusive_loadfile_scheduling import ExclusiveLoadFileScheduling, EXCLUSIVE_TEST_SCOPE_PREFIX

@pytest.fixture
def exclusive_tests_mock():
    with patch('xdist_scheduling_exclusive.exclusive_loadfile_scheduling.load_exclusive_tests') as mock:
        mock.return_value = ['test_exclusive_1', 'test_exclusive_2']
        yield mock

@pytest.fixture
def config_mock():
    """Mock the config object to simulate the --tx option being set."""
    mock = Mock()
    mock.getvalue.return_value = ["popen//python=python"]
    mock.option.tx = ["popen//python=python"]
    return mock


@pytest.fixture
def log_mock():
    # Mock the log object
    return Mock()


def test_exclusive_group_file_scheduling_init(exclusive_tests_mock, config_mock, log_mock):
    scheduler = ExclusiveLoadFileScheduling(config_mock, log_mock)
    # Verify that load_exclusive_tests was called and exclusive_tests attribute is correctly set
    exclusive_tests_mock.assert_called_once()
    assert len(scheduler.exclusive_tests) == 2


def test_split_scope_exclusive(exclusive_tests_mock, config_mock, log_mock):
    scheduler = ExclusiveLoadFileScheduling(config_mock, log_mock)
    nodeid = 'test_exclusive_1'
    scope = scheduler._split_scope(nodeid)
    assert scope.startswith(EXCLUSIVE_TEST_SCOPE_PREFIX)


def test_split_scope_regular(exclusive_tests_mock, config_mock, log_mock):
    scheduler = ExclusiveLoadFileScheduling(config_mock, log_mock)
    nodeid = 'test_regular_1'
    with patch('xdist_scheduling_exclusive.exclusive_loadfile_scheduling.LoadFileScheduling._split_scope') as super_split_scope_mock:
        super_split_scope_mock.return_value = 'regular_scope'
        scope = scheduler._split_scope(nodeid)
        assert scope == 'regular_scope'
        super_split_scope_mock.assert_called_once_with(nodeid)
