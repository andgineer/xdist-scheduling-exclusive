[![Build Status](https://github.com/andgineer/xdist-scheduling-exclusive/workflows/CI/badge.svg)](https://github.com/andgineer/xdist-scheduling-exclusive/actions)
[![Coverage](https://raw.githubusercontent.com/andgineer/xdist-scheduling-exclusive/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/xdist-scheduling-exclusive/blob/python-coverage-comment-action-data/htmlcov/index.html)
# xdist-scheduling-exclusive

A pytest-xdist scheduler for running specific tests on dedicated workers.

## Features

- Improves test runtime by assigning long tests to separate workers
- Includes custom reporting in `conftest.py` to show test scheduling details

# Installation

```bash
pip install xdist-scheduling-exclusive pytest-xdist
```

# Usage

To integrate with your pytest setup, update conftest.py as follows:

```python
from xdist_scheduling_exclusive import ExclusiveLoadScopeScheduling

def pytest_xdist_make_scheduler(config, log):
    """xdist-pytest hook to set scheduler."""
    return ExclusiveLoadScopeScheduling(config, log)
```

And place exclusive tests file `exclusive_tests.txt` in `tests/resources/`.

You can get the list with pytest's
[--durations](https://docs.pytest.org/en/latest/how-to/usage.html#profiling-test-execution-duration)
option that also sort tests by execution time.
Do not forget to clear execution time from the file - there should be only test `node IDs`.
See example in this project `tests/resources/exclusive_tests.txt`.

Placing the slowest tests in `exclusive_tests.txt` will give you the most benefit.

### Available Schedulers:
- `ExclusiveLoadScheduling` Schedule tests from `exclusive_tests.txt` first and on dedicated nodes.
- `ExclusiveLoadFileScheduling`: Place tests from `exclusive_tests.txt` to unique `scopes`.
Other tests are grouped as in `--dist loadfile`: tests from the same file run on the same node.
- `ExclusiveLoadScopeScheduling`: Schedule tests from `exclusive_tests.txt` first and on dedicated nodes.
Other tests are grouped as in `--dist loadfile`: tests from the same file run on the same node.


# Developers
Do not forget to run `. ./activate.sh`.

To see how tests were scheduled use something like

    python -m pytest -n 4 --xdist-report -s

# Scripts
    make help

## Coverage report
* [Codecov](https://app.codecov.io/gh/andgineer/xdist-scheduling-exclusive/tree/main/src%2Fxdist_scheduling_exclusive)
* [Coveralls](https://coveralls.io/github/andgineer/xdist-scheduling-exclusive)
