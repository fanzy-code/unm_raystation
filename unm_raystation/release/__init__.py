import sys

from definitions import ROOT_DIR

ScriptClient_path = ROOT_DIR + "\\RS_ScriptClient\\"
connect_path = ROOT_DIR + "\\RS_ScriptClient\\connect\\"
sys.path.append(ScriptClient_path)
sys.path.append(connect_path)

release_path = ROOT_DIR + "\\unm_raystation\\release\\"
sys.path.append(release_path)

# Assemblies
dll_directory = ROOT_DIR + "\\assemblies\\"
sys.path.append(dll_directory)
import clr

clr.AddReference("System")  # System = System.dll
clr.AddReference("System.Windows")  # System.Windows = PresentationCore.dll
clr.AddReference("PresentationFramework")  # System.Windows.Controls = PresentationFramework.dll


import System
import System.Windows
import System.Windows.Controls
