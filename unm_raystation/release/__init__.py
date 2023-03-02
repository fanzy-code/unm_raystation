### this folders scripts with proper paths

import sys

from definitions import ROOT_DIR

ScriptClient_path = ROOT_DIR + "\\RS_ScriptClient\\"
connect_path = ROOT_DIR + "\\RS_ScriptClient\\connect\\"
sys.path.append(ScriptClient_path)
sys.path.append(connect_path)
