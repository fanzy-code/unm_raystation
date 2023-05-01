""" 
Utility functions to for RayStation Dicom related networking.  
Classes to define DicomSCP, AnonymizationSettings for DCM Export, and a GUI for to display multiple DICOM Export Destinations.

Installation:
Import, save, and validate this script in RayStation, ideally hidden from the clinical user.
Make sure to choose the appropriate environment so imports will work.

TODO:
...

"""
import copy
import json
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from util_raystation_general import get_current_helper

from connect import PyScriptObject


@dataclass
class DicomSCP:
    # Needs either Title or Node+Port+CalledAE+CallingAE
    Title: Optional[str] = None

    Node: Optional[str] = None
    Port: Optional[str] = None
    CalledAE: Optional[str] = None
    CallingAE: Optional[str] = None
    _allowed_titles: List[str] = field(default_factory=list)

    def __str__(self):
        if self.Title:
            return str(self.Title)
        else:
            return str(self.Node)

    def get_dicomscp_dict(self) -> Dict:
        excluded_attrs = ["_allowed_titles"]
        return {k: v for k, v in vars(self).items() if v is not None and k not in excluded_attrs}

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
            # Query for allowed titles in ClinicDB
            if not (self._allowed_titles):
                try:
                    _clinic_db = get_current_helper("ClinicDB")
                    self._allowed_titles = [
                        AE.Title
                        for AE in _clinic_db.GetSiteSettings().DicomSettings.DicomApplicationEntities
                    ]
                except:
                    logging.warning("Unable to get titles from clinic_db")

            if not (self.Title in self._allowed_titles):
                raise ValueError(
                    f"Title {self.Title} does not exist in the clinical DB.  Existing ones are {self._allowed_titles}."
                )

        return


@dataclass
class AnonymizationSettings:
    Anonymize: bool = False
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
    AnonymizationSettings: AnonymizationSettings = AnonymizationSettings()

    # Supported
    Active_CT: bool = False
    _Examinations: Optional[List[str]] = None  # Example [examination.Name]

    # Supported
    RtStructureSet_from_Active_CT: bool = False
    _RtStructureSetsForExaminations: Optional[List[str]] = None  # Example [examination.Name]

    # Not supported
    _RtStructureSetsReferencedFromBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    Active_RTPlan: bool = False
    _BeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported
    _RtRadiationSetForBeamSets: Optional[
        List[str]
    ] = None  # CK only: Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported
    _RtRadiationsForBeamSets: Optional[
        List[str]
    ] = None  # CK only: Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    Active_BeamSet_Dose: bool = False
    _PhysicalBeamSetDoseForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not Supported; dose calculated with tissue hetereogeneity
    _EffectiveBeamSetDoseForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    Active_BeamSet_BeamDose: bool = False
    _PhysicalBeamDosesForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not Supported; beam doses calculated with tissue hetereogeneity
    _EffectiveBeamDosesForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported
    _SpatialRegistrationForExaminations: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(fromExamination.Name, toExamination.Name)]

    # Not supported
    _DeformableSpatialRegistrationsForExaminations: Optional[
        List[str]
    ] = None  # Example ["%s:%s:%s"%(case.PatientModel.StructureRegistrationGroups[0].Name, fromExamination.Name, toExamination.Name)]

    # Supported
    TxBeam_DRRs: bool = False
    _TreatmentBeamDrrImages: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    SetupBeam_DRRs: bool = False
    _SetupBeamDrrImages: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported, Custom DICOM .filter settings defined in Clinic Settings
    _DicomFilter: str = ""

    _IgnorePreConditionWarnings: bool = False

    # Supported, Choose one but not both
    Connection: Optional[DicomSCP] = None
    ExportFolderPath: Optional[str] = None

    def __post_init__(self):
        if not ((self.Connection is None) ^ (self.ExportFolderPath is None)):
            raise ValueError(
                "Either Connection or ExportFolderPath has to be defined, but not both"
            )
        return

    def update_with_beam_set(self, beam_set):
        # Extract kwargs from beam_set
        kwargs = {"machine_name": beam_set.MachineReference.MachineName}
        # Update ExportFolderPath

        updated_dcm_destination = copy.deepcopy(self)
        if updated_dcm_destination.ExportFolderPath:
            updated_dcm_destination.ExportFolderPath = (
                updated_dcm_destination.ExportFolderPath.format(**kwargs)
            )
        return updated_dcm_destination

    def generate_xaml_attribute_dict(self) -> Dict:
        xaml_dict = {
            "name": {
                "xaml_display": "Name",
                "xaml_name": f"{self.name}_name",
                "xaml_value": self.name,
            },
            "Connection": {
                "xaml_display": "DICOM Destination",
                "xaml_name": f"{self.name}_Connection",
                "xaml_value": self.Connection,
            },
            "ExportFolderPath": {
                "xaml_display": "Export Folder Path",
                "xaml_name": f"{self.name}_ExportFolderPath",
                "xaml_value": self.ExportFolderPath,
            },
            "Active_CT": {
                "xaml_display": "Active CT",
                "xaml_name": f"{self.name}_Active_CT",
                "xaml_value": self.Active_CT,
            },
            "RtStructureSet_from_Active_CT": {
                "xaml_display": "RT Structure Set",
                "xaml_name": f"{self.name}_RtStructureSet_from_Active_CT",
                "xaml_value": self.RtStructureSet_from_Active_CT,
            },
            "Active_RTPlan": {
                "xaml_display": "RT Plan",
                "xaml_name": f"{self.name}_Active_RTPlan",
                "xaml_value": self.Active_RTPlan,
            },
            "Active_BeamSet_Dose": {
                "xaml_display": "BeamSet Dose",
                "xaml_name": f"{self.name}_Active_BeamSet_Dose",
                "xaml_value": self.Active_BeamSet_Dose,
            },
            "Active_BeamSet_BeamDose": {
                "xaml_display": "Beam Dose",
                "xaml_name": f"{self.name}_Active_BeamSet_BeamDose",
                "xaml_value": self.Active_BeamSet_BeamDose,
            },
            "TxBeam_DRRs": {
                "xaml_display": "Tx Beam DRRs",
                "xaml_name": f"{self.name}_TxBeam_DRRs",
                "xaml_value": self.TxBeam_DRRs,
            },
            "SetupBeam_DRRs": {
                "xaml_display": "Setup Beam DRRs",
                "xaml_name": f"{self.name}_SetupBeam_DRRs",
                "xaml_value": self.SetupBeam_DRRs,
            },
        }

        return OrderedDict(xaml_dict)

    def get_export_kwargs(self) -> Dict[str, Any]:
        # Prepares the export kwargs dictionary for ScriptableDicomExport function

        # Initialize with all variables leading with '_'
        export_kwargs = {
            var_name.lstrip("_"): var_value
            for var_name, var_value in vars(self).items()
            if (var_name.startswith("_") and var_value)
        }

        # Pick a connection type
        if self.Connection and self.ExportFolderPath:
            raise ValueError("Both Connection and ExportFolderPath cannot be defined.")

        if self.Connection:
            export_kwargs["Connection"] = self.Connection.get_dicomscp_dict()
        elif self.ExportFolderPath:
            export_kwargs["ExportFolderPath"] = self.ExportFolderPath
        else:
            raise ValueError("Either Connection or ExportFolderPath must be defined.")

        export_kwargs[
            "AnonymizationSettings"
        ] = self.AnonymizationSettings.get_anonymization_settings_dict()

        return export_kwargs

    def set_export_arguments(
        self, examination: PyScriptObject, beam_set: PyScriptObject  # type: ignore
    ) -> list:
        if examination is None:
            raise ValueError("No examination provided")
        if beam_set is None:
            raise ValueError("No beam set provided")

        # Hashmap for class attribute variables to export arguments needed for export
        settings_to_export_arguments = {
            "Active_CT": {"_Examinations": [examination.Name]},
            "RtStructureSet_from_Active_CT": {
                "_RtStructureSetsForExaminations": [examination.Name]
            },
            "Active_RTPlan": {"_BeamSets": [beam_set.BeamSetIdentifier()]},
            "Active_BeamSet_Dose": {
                "_PhysicalBeamSetDoseForBeamSets": [beam_set.BeamSetIdentifier()]
            },
            "Active_BeamSet_BeamDose": {
                "_PhysicalBeamDosesForBeamSets": [beam_set.BeamSetIdentifier()]
            },
            "TxBeam_DRRs": {"_TreatmentBeamDrrImages": [beam_set.BeamSetIdentifier()]},
            "SetupBeam_DRRs": {"_SetupBeamDrrImages": [beam_set.BeamSetIdentifier()]},
        }

        attr_was_set = []
        for attr, props in settings_to_export_arguments.items():
            if getattr(self, attr):
                attr_was_set.append(attr)
                for prop, value in props.items():
                    setattr(self, prop, value)

        return attr_was_set

    def handle_result(self, result: str) -> str:
        try:
            json_string = json.loads(str(result))
            comment_block: str = json_string["Comment"]
            warnings: List[str] = json_string["Warnings"]
            notifications: List[str] = json_string["Notifications"]

            warnings_block = "\n".join(warnings)
            notifications_block = "\n".join(notifications)

            result = f"Comment:\n{comment_block}\n\nWarnings:\n{warnings_block}\n\nNotifications:\n{notifications_block}"

        except ValueError as error:
            logging.info(result)
            # raise_error(f"Error reading completion message.", error)

        return result

    def generate_gui_message(self, beam_set_name, success: bool, result=None) -> Tuple[str, str]:
        log_message = ""
        if self.ExportFolderPath:
            name = self.ExportFolderPath
        if self.Connection:
            name = str(self.Connection)

        if success:
            status_message = "COMPLETE"
            log_message = (
                f"{beam_set_name} export to {self.name} (Node/Path: {name}) ... COMPLETE\n\n"
            )
        else:
            status_message = "Error"
            log_message = f"{beam_set_name} export to {self.name} (Node/Path: {name})... Error\n\n"

        if result:
            log_message += self.handle_result(result)

        # Add some new lines for next set of log messages
        log_message += "\n\n\n"
        return status_message, log_message

    def handle_log_warnings(self, error):
        logging.info(
            f"Error exporting, changing to IgnorePreConditionWarnings = True.  Raw error variable string: {error}"
        )
        return

    def export(self, case: PyScriptObject, examination: PyScriptObject, beam_set: PyScriptObject) -> (str, str):  # type: ignore
        attr_was_set = self.set_export_arguments(examination, beam_set)
        if not attr_was_set:
            status_message = "SKIPPED"
            log_message = (
                f"Beam set {beam_set.DicomPlanLabel} export to {self.name}... SKIPPED\n\n"
            )
            print(log_message)
            return status_message, log_message

        export_kwargs = self.get_export_kwargs()

        try:
            print(
                f"Exporting beam set {beam_set.DicomPlanLabel} to {self.name}, ignoring warnings"
            )
            export_kwargs["IgnorePreConditionWarnings"] = True
            result = case.ScriptableDicomExport(**export_kwargs)
            status_message, log_message = self.generate_gui_message(
                beam_set_name=beam_set.DicomPlanLabel, success=True, result=result
            )
        except Exception as error:
            print(error)
            status_message, log_message = self.generate_gui_message(
                beam_set_name=beam_set.DicomPlanLabel, success=False, result=str(error)
            )
            logging.info(f"Export incomplete, {error}")

        return status_message, log_message
