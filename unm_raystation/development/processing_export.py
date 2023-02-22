"""
Script to export plans to multiple locations
"""

import json
from dataclasses import dataclass, field


@dataclass
class DCMExportDestination:
    """Class to configure DICOM export destination options"""

    name: str

    class AnonymizationSettings:
        # Anonymization settings
        anonymize: bool = False
        AnonymizedName: str = "anonymizedName"
        AnonymizedID: str = "anonymizedID"
        RetainDates: bool = False
        RetainDeviceIdentity: bool = False
        RetainInstitutionIdentity: bool = False
        RetainUIDS: bool = False
        RetainSafePrivateAttributes: bool = False

    d = AnonymizationSettings().__dict__

    anonymization_settings: dict = field(default_factory=d)

    def __post_init__(self):
        print(self.anonymization_settings)

    def handle_log_completion(self, result):
        return

    def handle_log_warnings(self, error):
        return

    def handle_log_errors(self, error):
        return

    def export(self):
        return


def main():
    test_dicom_destination = DCMExportDestination(name="test_destination")


if __name__ == "__main__":
    main()
