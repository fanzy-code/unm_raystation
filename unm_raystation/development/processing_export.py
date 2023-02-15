"""
Script to export plans to multiple locations
"""

from dataclasses import dataclass


@dataclass
class DCMExportDestination:
    """Class to configure DICOM export destination options"""

    name: str

    def handle_log_warnings(self):
        return

    def handle_log_errors(self):
        return

    def export(self):
        return
