import sys

import clr  # type: ignore

from definitions import ROOT_DIR

dll_directory = ROOT_DIR + "\\assembilies\\"
sys.path.append(dll_directory)

clr.AddReference("System")  # System = System.dll
clr.AddReference("System.Windows")  # System.Windows = PresentationCore.dll
clr.AddReference("PresentationFramework")  # System.Windows.Controls = PresentationFramework.dll
