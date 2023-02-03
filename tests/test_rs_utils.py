"""
pytest for rs_utils 
"""

__author__ = "Michael Fan"
__version__ = "0.1.0"
__license__ = "MIT"

### Initialize the test environment by adding paths to ScriptClient.dll and connect module
import sys

from definitions import ROOT_DIR

ScriptClient_path = ROOT_DIR + "\\RS_ScriptClient\\"
connect_path = ROOT_DIR + "\\RS_ScriptClient\\connect\\"
sys.path.append(ScriptClient_path)
sys.path.append(connect_path)
###

import logging

import pytest

import unm_raystation.release.rs_utils


def test_raise_error():
    error_message = "test message"
    with pytest.raises(Exception) as exception_error:
        raise_error(error_message, exception_error)
