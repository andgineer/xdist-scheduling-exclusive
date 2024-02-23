import pytest
from unittest.mock import Mock, patch, mock_open
from xdist_scheduling_exclusive.exclusive_scheduling import ExclusiveScheduling  # Update with the actual path to your module


@pytest.fixture
def mock_exclusive_scheduling():
    # Patch the __init__ method of the parent class to prevent it from running
    with patch('xdist_scheduling_exclusive.exclusive_scheduling.ExclusiveScheduling.__init__', return_value=None):
        return ExclusiveScheduling(Mock(), Mock())


def test_exclusive_scheduling_load_exclusive_tests(mock_exclusive_scheduling):
    with patch("builtins.open", mock_open(read_data="exclusive_test_1\nexclusive_test_2")) as mock_file:
        exclusive_tests = mock_exclusive_scheduling.load_exclusive_tests()
        mock_file.assert_called_once_with("tests/resources/exclusive_tests.txt", "r", encoding="utf8")
        assert exclusive_tests == ["exclusive_test_1", "exclusive_test_2"]


def test_exclusive_scheduling_exclusive_tests_indices(mock_exclusive_scheduling):
    mock_exclusive_scheduling.collection = ["test_1", "exclusive_test_1", "test_2", "exclusive_test_2"]
    mock_exclusive_scheduling.exclusive_tests = ["exclusive_test_1", "exclusive_test_2"]

    indices = mock_exclusive_scheduling.exclusive_tests_indices
    assert indices == [1, 3]  # Indexes of exclusive tests in the collection
