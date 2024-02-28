"""pytest-xdist scheduler that runs some tests on dedicated workers.

Can significantly improve runtime by running long tests on separate workers.
"""
from xdist_scheduling_exclusive.exclusive_load_scheduling import ExclusiveLoadScheduling
from xdist_scheduling_exclusive.exclusive_loadfile_scheduling import ExclusiveLoadFileScheduling
from xdist_scheduling_exclusive.exclusive_loadscope_scheduling import ExclusiveLoadScopeScheduling

__all__ = ["ExclusiveLoadScheduling", "ExclusiveLoadFileScheduling", "ExclusiveLoadScopeScheduling"]
