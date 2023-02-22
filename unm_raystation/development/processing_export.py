"""
Script to export plans to multiple locations
"""

import json
from dataclasses import dataclass, field


@dataclass
class AnonymizationSettings:
    anonymize: bool = False
    AnonymizedName: str = "anonymizedName"
    AnonymizedID: str = "anonymizedID"
    RetainDates: bool = False
    RetainDeviceIdentity: bool = False
    RetainInstitutionIdentity: bool = False
    RetainUIDS: bool = False
    RetainSafePrivateAttributes: bool = False

    def get_anonymization_settings(self) -> dict:
        return self.__dict__


@dataclass
class DCMExportDestination:
    name: str
    anonymization_settings: AnonymizationSettings

    def handle_log_completion(self, result):
        return

    def handle_log_warnings(self, error):
        return

    def handle_log_errors(self, error):
        return

    def export(self):
        return


def main():
    test_anon_settings = AnonymizationSettings()
    test_dicom_destination = DCMExportDestination("test_destination", test_anon_settings)


if __name__ == "__main__":
    main()
