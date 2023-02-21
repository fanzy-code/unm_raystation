# mypy: ignore-errors
import platform

if platform.python_implementation() == "IronPython":
    from .connect_ironpython import *
else:
    from .connect_cpython import *
    from .ray_window import RayWindow
