import time

import pytest


@pytest.mark.exclusive
def test_exclusive_1():
    # Simulate test execution time
    time.sleep(1)