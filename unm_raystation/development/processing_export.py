"""
Script to export plans to multiple locations
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import System
from connect import PyScriptObject, get_current  # type: ignore
from rs_utils import raise_error

# Query clinical DB titles
clinic_db = get_current("ClinicDB")
production_dicomscp_titles = [
    AE.Title for AE in clinic_db.GetSiteSettings().DicomSettings.DicomApplicationEntities
]


# production_dicomscp_titles = [
#     "Velocity",
#     "MOSAIQ",
#     "Tomotherapy",
#     "PACS",
#     "LifeImage",
#     "SunCheck",
#     "Eclipse",
# ]


@dataclass
class DicomSCP:
    # Needs either Title or Node+Port+CalledAE+CallingAE
    Title: Optional[str] = None

    Node: Optional[str] = None
    Port: Optional[str] = None
    CalledAE: Optional[str] = None
    CallingAE: Optional[str] = None
    _allowed_titles: List[str] = []

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

        if self.Title:
            try:
                _clinic_db = get_current("ClinicDB")
                self._allowed_titles = [
                    AE.Title
                    for AE in _clinic_db.GetSiteSettings().DicomSettings.DicomApplicationEntities
                ]
            except:
                logging.warn("Unable to get titles from clinic_db")

            if not (self.Title in self._allowed_titles):
                raise ValueError(
                    f"Title {self.Title} does not exist in the clinical DB.  Existing ones are {self._allowed_titles}."
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
    Examinations: List[str]  # Example [examination.Name]
    RtStructureSetsForExaminations: List[str]  # Example [examination.Name]

    # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]
    RtStructureSetsReferencedFromBeamSets: List[str]

    # CK only: Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]
    RtRadiationSetForBeamSets: List[str]

    # CK only: Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]
    RtRadiationsForBeamSets: List[str]

    # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]
    PhysicalBeamSetDoseForBeamSets: List[str]

    # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]
    EffectiveBeamSetDoseForBeamSets: List[str]

    # Example ["%s:%s"%(fromExamination.Name, toExamination.Name)]
    SpatialRegistrationForExaminations: List[str]

    # Example ["%s:%s:%s"%(case.PatientModel.StructureRegistrationGroups[0].Name, fromExamination.Name, toExamination.Name)]
    DeformableSpatialRegistrationsForExaminations: List[str]

    # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]
    TreatmentBeamDrrImages: List[str]

    # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]
    SetupBeamDrrImages: List[str]

    # Custom DICOM .filter settings defined in Clinic Settings
    DicomFilter: str = ""

    IgnorePreConditionWarnings: bool = False

    # Choose one but not both
    Connection: Optional[DicomSCP] = None
    ExportFolderPath: Optional[str] = None

    def __post_init__(self):
        if not ((self.Connection is None) ^ (self.ExportFolderPath is None)):
            raise ValueError(
                "Either Connection or ExportFolderPath has to be defined, but not both"
            )
        return

    # Get rid of these print statements and put it in logging or something
    def handle_log_completion(self, result):
        try:
            jsonWarnings = json.loads(str(result))
            print("Completed!")
            print("Comment:")
            print(jsonWarnings["Comment"])
            print("Warnings:")
            for w in jsonWarnings["Warnings"]:
                print(w)
            print("Export notifications:")
            # Export notifications is a list of notifications that the user should read.
            for w in jsonWarnings["Notifications"]:
                print(w)
        except ValueError as error:
            raise_error(f"Error reading completion message.", error)

    def handle_log_warnings(self, error):
        try:
            jsonWarnings = json.loads(str(error))
            # If the json.loads() works then the script was stopped due to
            # a non-blocking warning.
            print("WARNING! Export Aborted!")
            print("Comment:")
            print(jsonWarnings["Comment"])
            print("Warnings:")

            # Here the user can handle the warnings. Continue on known warnings,
            # stop on unknown warnings.
            for w in jsonWarnings["Warnings"]:
                print(w)
        except ValueError as error:
            raise_error(f"DICOM export unsuccessful.  Error reading warning message.", error)

    def handle_log_errors(self, error):
        raise_error(f"Error exporting DICOM", error)
        return

    def export(self, case: PyScriptObject):
        export_kwargs = vars(self)

        try:
            result = case.ScriptableQADicomExport(**export_kwargs)
            self.handle_log_completion(result)
        except System.InvalidOperationException as error:
            self.handle_log_warnings(error)
            export_kwargs["IgnorePreConditionWarnings"] = True
            result = case.ScriptableQADicomExport(**export_kwargs)
            self.handle_log_completion(result)
        except Exception as error:
            self.handle_log_errors(error)

        return


def main():
    case = get_current("Case")
    # figure some stuff out about the case in question, error checks and such

    examination = get_current("Examination")

    # Test definition

    velocity_dicomscp = DicomSCP(Title="Velocity")
    velocity_destination_anonymization_settings = AnonymizationSettings()
    velocity_dcm_export_destination = DCMExportDestination(
        "Velocity", velocity_destination_anonymization_settings, Connection=velocity_dicomscp
    )

    velocity_dcm_export_destination.export(case)

    # Initialize the GUI
    # show the destinations
    # clicking the export should initialize the for loop through the destinations and run self.export
    # during this time, errors have to be handled


if __name__ == "__main__":
    main()
