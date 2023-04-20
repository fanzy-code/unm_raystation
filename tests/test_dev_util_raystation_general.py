"""
pytest for rs_utils 
"""

__author__ = "Michael Fan"
__version__ = "1.0.0"
__license__ = "MIT"

### Library for running tests
import datetime
import logging

import pydicom as dicom
import pytest

from unm_raystation.development.util_raystation_general import (
    get_current_helper,
    raise_error,
    slugify,
)


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
