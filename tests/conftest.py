import pytest
import time
import json
import os
from datetime import datetime
from tempfile import gettempdir

from xdist_scheduling_exclusive import ExclusiveLoadScopeScheduling  # noqa
from xdist_scheduling_exclusive import ExclusiveLoadScheduling  # noqa
from xdist_scheduling_exclusive import ExclusiveLoadFileScheduling  # noqa

XDIST_REPORT_OPTION = "--xdist-report"

# Define the directory for data storage.
DATA_DIR = os.path.join(gettempdir(), "xdist_data")


@pytest.fixture(autouse=True)
def let_xdist_tick():
    """Let xdist tick."""
    time.sleep(0.01)


def pytest_xdist_make_scheduler(config, log):
    """xdist-pytest hook to set scheduler."""
    # return ExclusiveLoadScopeScheduling(config, log)
    # return ExclusiveLoadScheduling(config, log)
    return ExclusiveLoadFileScheduling(config, log)


def ensure_execution_data_dir_exists():
    """Ensures the execution data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Executed at the start of the pytest session."""
    if session.config.getoption(XDIST_REPORT_OPTION):
        ensure_execution_data_dir_exists()
        # Cleanup if not empty.
        for filename in os.listdir(DATA_DIR):
            os.remove(os.path.join(DATA_DIR, filename))
        # Store the session start time.
        session.start_time = time.time()

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Setup for each test item."""
    if item.config.getoption(XDIST_REPORT_OPTION):
        # Always capture start time; the flag will determine if we write data later.
        item.execution_start_time = time.time()

def pytest_runtest_teardown(item, nextitem):
    """Teardown for each test item."""
    if item.config.getoption(XDIST_REPORT_OPTION):
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
                     help="Collect exclusive test execution times")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Executed at the end of the pytest session for generating a summary report."""
    if config.getoption(XDIST_REPORT_OPTION):
        if not os.path.exists(DATA_DIR):
            print("\nNo execution data directory found.")
            return

        print("\nTest Execution Summary:")
        for filename in sorted(os.listdir(DATA_DIR)):
            file_path = os.path.join(DATA_DIR, filename)
            with open(file_path, 'r') as f:
                execution_data = json.load(f)
                # Calculate and format the execution time as MM:SS from the session start.
                start_time_formatted = f"{execution_data['start_time']:.3f}"
                end_time_formatted = f"{execution_data['end_time']:.3f}"
                print(f"{execution_data['worker']:>4} {'EXCLUSIVE' if execution_data['exclusive'] else '':10} {start_time_formatted} .. {end_time_formatted} - {execution_data['nodeid']}")

