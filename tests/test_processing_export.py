import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


# Define the mock_util_raystation_networking module
class MockDicomSCP:
    def __init__(self, *args, **kwargs):
        pass


class MockDCMExportDestination:
    def __init__(self, *args, **kwargs):
        pass


mock_util_raystation_networking = MagicMock()
mock_util_raystation_networking.DicomSCP = MockDicomSCP
mock_util_raystation_networking.DCMExportDestination = MockDCMExportDestination

sys.modules["util_raystation_networking"] = mock_util_raystation_networking
# Add the DicomSCP and DCMExportDestination classes to the module
mock_util_raystation_networking = MagicMock()
mock_util_raystation_networking.DicomSCP = MockDicomSCP
mock_util_raystation_networking.DCMExportDestination = MockDCMExportDestination

sys.modules["util_raystation_networking"] = mock_util_raystation_networking


def test_processing_export_gui_import(monkeypatch):
    from unm_raystation.release.processing_export import ProcessingExportGUI


# I am unable to create reasonable tests to test the ProcessingExportGUI class, there are API calls which I cannot mock properly
