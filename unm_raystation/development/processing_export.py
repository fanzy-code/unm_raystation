"""
Script to export plans to multiple locations
"""

import json
from dataclasses import dataclass, field
from typing import Optional

# Can I just query this??
production_dicomscp_list = [
    "Velocity",
    "MOSAIQ",
    "Tomotherapy",
    "PACS",
    "LifeImage",
    "SunCheck",
    "Eclipse",
]


@dataclass
class DicomSCP:
    # Needs either Title or Node+Port+CalledAE+CallingAE
    Title: Optional[str] = None

    Node: Optional[str] = None
    Port: Optional[str] = None
    CalledAE: Optional[str] = None
    CallingAE: Optional[str] = None

    def get_dicomscp_dict(self) -> dict:
        return {k: v for k, v in vars(self).items() if v is not None}

    def __post_init__(self):
        if not self.Title and not all((self.Node, self.Port, self.CalledAE, self.CallingAE)):
            raise ValueError(
                "Either Title or all of (Node, Port, CalledAE, CallingAE) have to be defined."
            )

        if self.Title and any((self.Node, self.Port, self.CalledAE, self.CallingAE)):
            raise ValueError(
                "Both Title and (Node, Port, CalledAE, CallingAE) are defined, only one can be."
            )

        return


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

    def get_anonymization_settings_dict(self) -> dict:
        return vars(self)


@dataclass
class DCMExportDestination:
    name: str
    AnonymizationSettings: AnonymizationSettings

    # Choose one but not both
    Connection: Optional[DicomSCP] = None
    ExportFolderPath: Optional[str] = None

    def __post_init__(self):
        if not ((self.Connection is None) ^ (self.ExportFolderPath is None)):
            raise ValueError(
                "Either Connection or ExportFolderPath has to be defined, but not both"
            )
        return

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
    test_dicomscp = DicomSCP(Title="Velocity")
    test_dicomscp = DicomSCP(Title="Velocity", Node="1", Port="1", CalledAE="1")
    # test_dicomscp = DicomSCP(Node="1", Port="1", CalledAE="1", CallingAE="1")
    test_dicom_destination = DCMExportDestination(
        "test_destination", test_anon_settings, Connection=test_dicomscp, ExportFolderPath=None
    )


if __name__ == "__main__":
    main()
