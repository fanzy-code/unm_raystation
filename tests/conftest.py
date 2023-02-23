import sys
import types

# Initialize testing environment
from definitions import ROOT_DIR

ScriptClient_path = ROOT_DIR + "\\RS_ScriptClient\\"
connect_path = ROOT_DIR + "\\RS_ScriptClient\\connect\\"
environment_scripts_path = ROOT_DIR + "\\unm_raystation\\release\\"

sys.path.append(ScriptClient_path)
sys.path.append(connect_path)
sys.path.append(environment_scripts_path)


# Fake System
class System:
    class InvalidOperationException(Exception):
        pass

    def __init__(self):
        pass

    @property
    def invalid_operation_exception(self):
        raise self.InvalidOperationException("Invalid operation")


fake_system_module = types.ModuleType("System")
fake_system_module.__dict__["System"] = System

sys.modules["System"] = fake_system_module
