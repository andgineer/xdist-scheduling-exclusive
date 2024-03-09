import pytest
import time
import json
import os
from datetime import datetime
from tempfile import gettempdir

from xdist_scheduling_exclusive import ExclusiveLoadScopeScheduling  # noqa
from xdist_scheduling_exclusive import ExclusiveLoadScheduling  # noqa
from xdist_scheduling_exclusive import ExclusiveLoadFileScheduling  # noqa
from xdist_scheduling_exclusive.scheduler_base import load_exclusive_tests

XDIST_REPORT_OPTION = "--xdist-report"
VALIDATE_SCHEDULING_OPTION = "--validate-scheduling"

# Define the directory for data storage.
DATA_DIR = os.path.join(gettempdir(), "xdist_data")


@pytest.fixture(autouse=True)
def let_xdist_tick():
    """Let xdist tick."""
    time.sleep(0.01)


def pytest_xdist_make_scheduler(config, log):
    """xdist-pytest hook to set scheduler."""
    # return ExclusiveLoadScheduling(
    # return ExclusiveLoadFileScheduling(
    return ExclusiveLoadScopeScheduling(
        config,
        log,
        exclusive_tests=load_exclusive_tests(
            file_name="tests/resources/exclusive_tests.txt"
        ),
        # dedicate_nodes=True,
    )


def ensure_execution_data_dir_exists():
    """Ensures the execution data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Executed at the start of the pytest session."""
    if session.config.getoption(XDIST_REPORT_OPTION) or session.config.getoption(VALIDATE_SCHEDULING_OPTION):
        ensure_execution_data_dir_exists()
        # Cleanup if not empty.
        for filename in os.listdir(DATA_DIR):
            os.remove(os.path.join(DATA_DIR, filename))
        # Store the session start time.
        session.start_time = time.time()

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Setup for each test item."""
    if item.config.getoption(XDIST_REPORT_OPTION) or item.config.getoption(VALIDATE_SCHEDULING_OPTION):
        # Always capture start time; the flag will determine if we write data later.
        item.execution_start_time = time.time()

def pytest_runtest_teardown(item, nextitem):
    """Teardown for each test item."""
    if item.config.getoption(XDIST_REPORT_OPTION) or item.config.getoption(VALIDATE_SCHEDULING_OPTION):
        ensure_execution_data_dir_exists()
        # Use session's start time to calculate relative times.
        session_start_time = item.session.start_time
        execution_data = {
            "nodeid": item.nodeid,
            "start_time": item.execution_start_time - session_start_time,
            "end_time": time.time() - session_start_time,
            "worker": getattr(item.config, 'workerinput', {}).get('workerid', 'master'),
            "exclusive": "exclusive" in item.keywords
        }
        # Safe filename from nodeid
        filename = f"{item.nodeid.replace('/', '_').replace(':', '_').replace('::', '__')}.json"
        data_file_path = os.path.join(DATA_DIR, filename)
        with open(data_file_path, 'w') as f:
            json.dump(execution_data, f)


def pytest_addoption(parser):
    parser.addoption(XDIST_REPORT_OPTION, action="store_true", default=False,
                     help="Report scheduling results")
    parser.addoption(VALIDATE_SCHEDULING_OPTION, action="store_true", default=False,
                     help="Validate scheduling results")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Executed at the end of the pytest session for generating a summary report."""
    if config.getoption(XDIST_REPORT_OPTION) or config.getoption(VALIDATE_SCHEDULING_OPTION):
        xdist_report(terminalreporter, exitstatus, config)
    if config.getoption(VALIDATE_SCHEDULING_OPTION):
        validate_scheduling(terminalreporter, exitstatus, config)


def xdist_report(terminalreporter, exitstatus, config):
    if not os.path.exists(DATA_DIR):
        print("\nNo execution data directory found.")
        return

    print("\nTest Execution Summary:")
    for filename in sorted(os.listdir(DATA_DIR)):
        file_path = os.path.join(DATA_DIR, filename)
        with open(file_path, 'r') as f:
            execution_data = json.load(f)
            # Calculate and format the execution time as MM:SS from the session start.
            start_time = f"{execution_data['start_time']:.3f}"
            end_time = f"{execution_data['end_time']:.3f}"
            is_exclusive = execution_data['exclusive']
            node = execution_data['worker']
            node_id = execution_data['nodeid']
            print(f"{execution_data['worker']:>4} {'EXCLUSIVE' if is_exclusive else '':10} {start_time} .. {end_time} - {node_id}")


def validate_scheduling(terminalreporter, exitstatus, config):
    if not os.path.exists(DATA_DIR):
        print("\nNo execution data directory found.")
        return

    node_first_test_start_time = {}
    all_exclusive_tests = set()
    exclusive_started_first = set()

    print("\nvalidate scheduling result..")
    for filename in sorted(os.listdir(DATA_DIR)):
        file_path = os.path.join(DATA_DIR, filename)
        with open(file_path, 'r') as f:
            execution_data = json.load(f)
            # Calculate and format the execution time as MM:SS from the session start.
            start_time = f"{execution_data['start_time']:.3f}"
            end_time = f"{execution_data['end_time']:.3f}"
            is_exclusive = execution_data['exclusive']
            node = execution_data['worker']
            node_id = execution_data['nodeid']

            if is_exclusive:
                all_exclusive_tests.add(node_id)

            if node not in node_first_test_start_time or start_time < node_first_test_start_time[node][0]:
                node_first_test_start_time[node] = (start_time, node_id, is_exclusive)

    for node, (start_time, node_id, is_exclusive) in node_first_test_start_time.items():
        if is_exclusive:
            exclusive_started_first.add(node_id)

    assert all_exclusive_tests == exclusive_started_first, (
        f"Validation failed: "
        f"{all_exclusive_tests - exclusive_started_first} exclusive tests did not start first on a node."
    )
    print("Validation passed: All exclusive tests were the first to run on separate nodes.")

