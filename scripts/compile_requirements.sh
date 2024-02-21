#!/usr/bin/env bash
#
# Pin current dependencies versions.
#

# pin test / lint / docs dependencies for reproducibility
uv pip compile requirements.dev.in

# pin requirements.in versions just as reference for potential incapability bugs in future
uv pip compile requirements.in

# do not pin dependencies in the package
scripts/include_pyproject_requirements.py requirements.in
