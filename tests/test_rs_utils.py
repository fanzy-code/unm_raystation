"""
pytest for rs_utils 
"""

__author__ = "Michael Fan"
__version__ = "0.1.0"
__license__ = "MIT"

import sys

import pytest

from definitions import ROOT_DIR

ScriptClient_path = ROOT_DIR + "\\RS_ScriptClient\\"
connect_path = ROOT_DIR + "\\RS_ScriptClient\\connect"
sys.path.append(ScriptClient_path)
sys.path.append(connect_path)

# sys.path.append(connect_path)
from connect import get_current

import unm_raystation.release.rs_utils

# @pytest.fixture
# def add_paths():
#     ScriptClient_path = ROOT_DIR + "\\RS_ScriptClient\\"
#     connect_path = ROOT_DIR + "\\RS_ScriptClient\\connect"
#     sys.path.append(ScriptClient_path)
#     sys.path.append(connect_path)
#     return


def test_raise_error():
    error_message = "test message"
    with pytest.raises(Exception) as exception_error:
        raise_error(error_message, exception_error)
