### Initialize the test environment by adding paths to ScriptClient.dll and connect module
import os
import sys
import types

from definitions import ROOT_DIR

# Add the parent directory of the __init__.py file to the path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# Add this directory containing the script to the path
development_path = ROOT_DIR + "\\unm_raystation\\development\\"
sys.path.append(development_path)

release_path = ROOT_DIR + "\\unm_raystation\\release\\"
sys.path.append(release_path)


# Add the RayStation ScriptClient and connect directories to the path
ScriptClient_path = ROOT_DIR + "\\RS_ScriptClient\\"
sys.path.append(ScriptClient_path)

connect_path = ROOT_DIR + "\\RS_ScriptClient\\connect\\"
sys.path.append(connect_path)

# Assemblies
dll_directory = ROOT_DIR + "\\assemblies\\"
sys.path.append(dll_directory)


import clr  # type: ignore

clr.AddReference("System")  # System = System.dll
clr.AddReference("System.Windows")  # System.Windows = PresentationCore.dll
# clr.AddReference("System.Runtime")
# clr.AddReference("System.Runtime.InteropServices")
