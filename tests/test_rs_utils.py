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

### Library for running tests
import datetime
import logging

import pytest

from unm_raystation.release.rs_utils import *


def test_raise_error():
    """
    Test the raise_error function raises exception correctly and the pytest environment imports packages appropriately
    """
    error_message = "test message"
    with pytest.raises(Exception) as exception_error:
        raise_error("test message", exception_error)


def test_get_current_helper():
    """
    Test to see an exception is raised for getting Patient
    """

    input = "Test_Bad_Input"
    with pytest.raises(ValueError) as exception_error:
        get_current_helper(input)

    # Will raise exception because we are not connected to a RayStation instance
    input = "Patient"
    with pytest.raises(Exception) as exception_error:
        get_current_helper(input)


def test_slugify():
    test_string = 'test/pl\\an-b/lah_"foo:*<>|'
    assert slugify(test_string) == "testplan-blah_foo"


def test_get_new_filename():
    test_filename = "foo/bar/file.dcm"  # assume safe input
    now = datetime.datetime.now().strftime("_%Y-%m-%d_%H-%M-%S")
    assert get_new_filename(test_filename) == "file" + now + ".dcm"
