import time

import pytest


def test_non_exclusive_1():
    # Simulate test execution time
    time.sleep(0.05)


@pytest.mark.exclusive
def test_exclusive_1():
    # Simulate test execution time
    time.sleep(0.05)


def test_non_exclusive_2():
    # Simulate test execution time
    time.sleep(0.5)


@pytest.mark.exclusive
def test_exclusive_2():
    # Simulate test execution time
    time.sleep(0.05)