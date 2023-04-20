import sys

from definitions import ROOT_DIR

dll_directory = ROOT_DIR + "\\assembilies\\"
sys.path.append(dll_directory)

import platform

if platform.python_implementation() == "IronPython":
    from .connect_ironpython import *
else:
    from .connect_cpython import *  # type: ignore
    from .ray_window import RayWindow
