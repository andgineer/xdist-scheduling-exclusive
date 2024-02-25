import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from xdist_scheduling_exclusive import ExclusiveLoadScheduling
from xdist_scheduling_exclusive.load_exclusive_tests import load_exclusive_tests


@pytest.fixture
def mock_exclusive_scheduling():
    # Patch the __init__ method of the parent class to prevent it from running
    with patch('xdist_scheduling_exclusive.exclusive_load_scheduling.ExclusiveLoadScheduling.__init__', return_value=None):
        exclusive_scheduling = ExclusiveLoadScheduling(Mock(), Mock())
        exclusive_scheduling.node2pending = MagicMock()  # Mocking the node2pending attribute
        exclusive_scheduling.collection = MagicMock()  # Mocking the collection if necessary
        exclusive_scheduling.pending = MagicMock()  # Mocking the pending list
        return exclusive_scheduling


def test_exclusive_scheduling_load_exclusive_tests(mock_exclusive_scheduling):
    with patch("builtins.open", mock_open(read_data="exclusive_test_1\nexclusive_test_2")) as mock_file:
        exclusive_tests = load_exclusive_tests()
        mock_file.assert_called_once_with("tests/resources/exclusive_tests.txt", "r", encoding="utf8")
        assert exclusive_tests == ["exclusive_test_1", "exclusive_test_2"]


def test_exclusive_scheduling_exclusive_tests_indices(mock_exclusive_scheduling):
    mock_exclusive_scheduling.collection = ["test_1", "exclusive_test_1", "test_2", "exclusive_test_2"]
    mock_exclusive_scheduling.exclusive_tests = ["exclusive_test_1", "exclusive_test_2"]

    indices = mock_exclusive_scheduling.exclusive_tests_indices
    assert indices == [1, 3]  # Indexes of exclusive tests in the collection


def test_send_exclusive_test_to_node(mock_exclusive_scheduling):
    mock_node = Mock()
    mock_exclusive_scheduling.collection = ["test_1", "exclusive_test_1"]
    mock_exclusive_scheduling.exclusive_tests = ["exclusive_test_1"]
    mock_exclusive_scheduling.pending = [1]  # Assuming index 1 is an exclusive test

    mock_exclusive_scheduling._send_tests(mock_node, 1)
    assert 1 not in mock_exclusive_scheduling.pending
    mock_node.send_runtest_some.assert_called_once_with([1])


def test_exclusive_test_not_in_collection(mock_exclusive_scheduling):
    mock_exclusive_scheduling.collection = ["test_1", "test_2"]
    mock_exclusive_scheduling.exclusive_tests = ["exclusive_test_1"]
    # Exclusive test is not in the collection, so indices should be empty
    assert mock_exclusive_scheduling.exclusive_tests_indices == []


def test_load_exclusive_tests_file_missing(mock_exclusive_scheduling):
    with patch("builtins.open", side_effect=FileNotFoundError()):
        with pytest.raises(ValueError) as exc_info:
            load_exclusive_tests("missing_file.txt")
            assert "Exclusive tests list 'missing_file.txt' not found." in str(exc_info.value)


def test_trace_functionality(mock_exclusive_scheduling, capsys):
    mock_exclusive_scheduling.trace("Test message")
    captured = capsys.readouterr()
    assert "Test message" in captured.err


def test_fallback_to_send_non_exclusive_when_no_exclusives_left(mock_exclusive_scheduling):
    mock_node = Mock()
    mock_exclusive_scheduling.collection = ["test_1", "test_2"]
    mock_exclusive_scheduling.exclusive_tests = []  # No exclusive tests
    mock_exclusive_scheduling.pending = [0, 1]  # Both tests are non-exclusive

    mock_exclusive_scheduling._send_tests(mock_node, 2)
    assert mock_exclusive_scheduling.pending == []
    mock_node.send_runtest_some.assert_called_once_with([0, 1])


def test_send_non_exclusive_test_to_node(mock_exclusive_scheduling):
    mock_node = Mock()
    mock_exclusive_scheduling.collection = ["test_1", "exclusive_test_2"]
    mock_exclusive_scheduling.exclusive_tests = ["exclusive_test_2"]
    mock_exclusive_scheduling.pending = [0]  # Assuming index 0 is a non-exclusive test

    mock_exclusive_scheduling._send_tests(mock_node, 1)
    assert 0 not in mock_exclusive_scheduling.pending
    mock_node.send_runtest_some.assert_called_once_with([0])