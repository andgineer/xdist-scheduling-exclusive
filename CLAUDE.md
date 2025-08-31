# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python package that extends pytest-xdist with custom test schedulers optimized for performance. The core concept is allowing "exclusive" tests (typically slow tests) to run on dedicated worker nodes to prevent resource contention during parallel execution.

## Development Commands

```bash
# Environment setup (creates venv with Python 3.12)
. ./activate.sh

# Install dependencies
make reqs

# Run tests with xdist scheduling
python -m pytest -n 4 --xdist-report

# Validate scheduling works correctly
python -m pytest -n 4 --validate-scheduling

# Run specific test types
python -m pytest tests/test_mock_exclusive.py -n 4
python -m pytest tests/test_exclusive_load_scheduling.py

# Linting (uses ruff with different line lengths: src=100, tests=99)
ruff check src/
ruff check tests/
mypy src/

# Version management
make ver-bug       # Bump patch version
make ver-feature   # Bump minor version
make ver-release   # Bump major version
```

## Architecture

### Core Scheduler Pattern
The project implements three scheduler strategies that extend pytest-xdist's base schedulers:

- **ExclusiveLoadScheduling**: Runs exclusive tests first on dedicated nodes, fills remaining capacity with non-exclusive tests
- **ExclusiveLoadFileScheduling**: Groups non-exclusive tests by file, places each exclusive test in unique scope
- **ExclusiveLoadScopeScheduling**: Most sophisticated with optional node dedication and priority scheduling

### Key Integration Points

**Plugin Hook**: Schedulers are integrated via `pytest_xdist_make_scheduler` hook in conftest.py:
```python
from xdist_scheduling_exclusive import ExclusiveLoadScopeScheduling

def pytest_xdist_make_scheduler(config, log):
    return ExclusiveLoadScopeScheduling(config, log)
```

**Test Configuration**: Exclusive tests are defined in `tests/resources/exclusive_tests.txt` (plain text, one test node ID per line)

**Execution Validation**: The test suite includes sophisticated scheduling validation that tracks worker assignments and timing to ensure exclusive tests run first on dedicated nodes.

### Source Structure

- `src/xdist_scheduling_exclusive/`: Main scheduler implementations
- `tests/`: Comprehensive test suite including unit tests, integration tests, and mock exclusive test scenarios
- `tests/conftest.py`: Contains both the scheduler hook and execution tracking/validation logic

## Testing Architecture

Tests use a multi-level validation approach:
1. **Unit tests** for individual schedulers
2. **Integration tests** that run actual xdist sessions with validation
3. **Mock exclusive tests** that simulate slow tests for scheduling verification

The `--validate-scheduling` flag enables runtime validation that exclusive tests run before non-exclusive tests on dedicated workers. The `--xdist-report` flag provides detailed execution summaries including timing and worker assignments.

## Build System

Uses modern Python packaging with:
- **hatchling** build backend (not setuptools)
- **uv** for fast dependency management
- **src/** layout with dynamic versioning from `__about__.py`
- Pre-commit hooks with ruff, mypy, and standard checks

## Development Notes

- Line length differs between source (100) and tests (99) due to ruff configuration
- CI tests across Python 3.9-3.12 on Ubuntu, macOS, and Windows
- MyPy configured with lenient missing import handling
- Coverage reporting integrated with multiple services (Codecov, Coveralls)
