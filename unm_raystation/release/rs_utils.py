""" 
Utility functions to assist with other RayStation Scripts.  Not meant to be ran on its own.

Installation:
Import, save, and validate this script in RayStation, ideally hidden from the clinical user.
Make sure to choose the appropriate environment so imports will work.

TODO:
...

"""

__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "1.1.0"
__license__ = "MIT"

import asyncio
import datetime
import glob
import itertools
import json
import logging
import os
import re
import shutil
import sys
import unicodedata
import warnings
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pydicom as dicom

# RayStation API
import System  # type: ignore
from connect import PyScriptObject, get_current  # type: ignore


def raise_error(error_message: str, rs_exception_error: Any) -> None:
    """
    RayStation API exception errors are not callable with custom messages.
    This function overrides passed rs_exception_error with a generic callable exception error.

    Args:
        error_message (str): Custom error message
        rs_exception_error (Exception): Exception error passed

    Raises:
        Exception: The passed exception
    """

    raise Exception(
        "{error_message}\n\nException: {rs_exception_error}".format(
            error_message=error_message, rs_exception_error=rs_exception_error
        )
    )


def get_current_helper(input: str) -> PyScriptObject:
    """
    Helper function for connect.get_current function from RayStation.
    Added error logging and messaging.

    Args:
        input (str): Supported inputs are "Patient", "Case", "Plan", "BeamSet", "Examination", "PatientDB", "MachineDB", "ClinicDB"

    Returns:
        PyScriptObject: The called class object
    """

    supported_types = [
        "Patient",
        "Case",
        "Plan",
        "BeamSet",
        "Examination",
        "PatientDB",
        "MachineDB",
        "ClinicDB",
    ]

    if input not in supported_types:
        error_message = f"{input} is not in supported types: {supported_types}."
        raise ValueError(error_message)

    try:
        output = get_current(input)
    except Exception as rs_exception_error:
        error_message = f"Unable to get {input}."
        raise_error(error_message=error_message, rs_exception_error=rs_exception_error)
    return output


def save_patient(patient: PyScriptObject) -> None:
    """
    Helper function for Patient.Save() function from Raystation.
    Patient class required as input, checks if modifications are made and saves the patient if so.

    Args:
        patient (PyScriptObject): patient object from RayStation API

    Returns:
        None

    """

    if patient.ModificationInfo == None:
        try:
            patient.Save()
        except Exception as rs_exception_error:
            error_message = "Unable to save patient."
            raise_error(error_message=error_message, rs_exception_error=rs_exception_error)
    return


def slugify(value: str, allow_unicode: bool = False) -> str:
    """
    Django's function for sanitizing strings for filenames and URLs.  Gold standard for making
    input strings URL and filename friendly.

    Modified to keep case instead of making everything lower case.

    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.

    Args:
        value (str): input string
        allow_unicode (bool, optional): See above. Defaults to False.

    Returns:
        str: string sanitized for safe URLs and file paths
    """

    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def get_new_filename(src_path: str) -> str:
    """
    Adds a timestamp to inbetween base filename and extension

    Args:
        src_path (str): path to file

    Returns:
        new_filename (str): new filename with timestamp
    """
    file = os.path.basename(src_path)
    base_name, extension = os.path.splitext(file)
    now = datetime.datetime.now().strftime("_%Y-%m-%d_%H-%M-%S")
    new_filename = base_name + now + extension
    return new_filename


def file_archive(src_path: str) -> str:
    """
    Helper function to archive a file.
    Takes input src_path for filepath.  Archive file in archive sub directory.

    Args:
        src_path (str): path of file to archive

    Returns:
        new_path (str): path of archived file
    """

    try:
        # Create new filename for copying destination
        new_filename = get_new_filename(src_path)

        # Make an Archive sub-directory if needed
        base_directory = os.path.dirname(src_path)
        archive_sub_directory = os.path.join(base_directory, "Archive")
        os.makedirs(archive_sub_directory, exist_ok=True)

        # Full path to destination
        new_path = os.path.join(archive_sub_directory, new_filename)
        shutil.move(src_path, new_path)

        return new_path

    except:
        raise Exception(f"Unable to archive file {src_path}")


def file_renamer(src_path: str, dst_path: str, delete: bool = True) -> str:
    """
    Helper function to assist with duplications when renaming files.

    delete=True will remove destination duplicate if they exist.
    delete=False will archive destination duplicate if they exist.

    Args:
        src_path (str): path of source file
        dst_path (str): path of destination file to be renamed to
        delete (bool, optional): See above. Defaults to True.

    Returns:
        str: Description of what was renamed
    """

    if os.path.exists(dst_path):
        if delete == True:
            os.remove(dst_path)
            logging.info(f"Duplicate found, deleted destination file: {dst_path}")

        elif delete == False:
            new_path = file_archive(src_path)
            logging.info(f"Duplicate found, archived destination file to: {new_path}")

    os.rename(src_path, dst_path)
    return f"Renamed {src_path} to {dst_path}"


class DicomNamer:
    """
    Class to extract data from Dicom RP and RD files for renaming purposes
    """

    # Filename placeholder strings
    RD_sum_filename_placeholder = "RD_Sum_{plan_name}"
    RD_beam_filename_placeholder = "RD_{beam_name}_{beam_description}"
    RP_filename_placeholder = "RP_{plan_name}"

    def __init__(self, dcm, new_patient_name: str = "", new_patient_id: str = ""):
        if not isinstance(dcm, dicom.dataset.FileDataset):
            raise TypeError("dcm must be an instance of pydicom.dataset.FileDataset")

        self.dcm = dcm
        self.last_name: str = ""
        self.first_name: str = ""
        self.middle_name: str = ""
        self.prefix_name: str = ""
        self.suffix_name: str = ""
        self.file_path: str = str(Path(str(dcm.filename)).resolve())
        self.root_dir: str = str(Path(str(dcm.filename)).resolve().parent)
        self.modality: str = dcm.Modality
        self.plan_name: str = ""
        self.SOPInstanceUID: str = dcm.SOPInstanceUID
        self.referenced_rtplan_uid: str = ""
        self.dose_summation_type: str = ""
        self.referenced_beam_number: str = ""
        self.beam_sequence: dict = {}
        self.beam_name: str = ""
        self.beam_description: str = ""

        self._need_save = self.replace_patient_attributes(new_patient_name, new_patient_id)

        self.set_dcm_patient_name()

        self.set_rd_rp_properties()

        if self._need_save:
            self.dcm.save_as(str(dcm.filename))

    def replace_patient_name(self, new_patient_name: str) -> bool:
        """
        Replaces patient name in dcm file instance

        Args:
            new_patient_name (str): new patient name

        Returns:
            boolean (bool): bool if a change was made
        """
        try:
            self.dcm.PatientName = new_patient_name
            return True
        except:
            raise Exception(f"Unable to set {self.dcm.PatientName} to {new_patient_name}")

    def replace_patient_id(self, new_patient_id: str) -> bool:
        """
        Replaces patient id in dcm file instance

        Args:
            new_patient_id (str): new patient id

        Returns:
            boolean (bool): bool if a change was made
        """
        try:
            self.dcm.PatientID = new_patient_id
            return True
        except:
            raise Exception(f"Unable to set {self.dcm.PatientID} to {new_patient_id}")

    def replace_patient_attributes(self, new_patient_name: str, new_patient_id: str) -> bool:
        """
        Wraps the replace patient name/id functions into control logic

        Args:
            new_patient_name (str): new patient name
            new_patient_id (str): new patient id

        Returns:
            boolean (bool): bool if a save was performed
        """
        save = False
        if new_patient_name:
            save = self.replace_patient_name(new_patient_name)

        if new_patient_id:
            save = self.replace_patient_id(new_patient_id)

        return save

    def read_dcm_patient_name(self, dcm_patient_name: str) -> dict:
        """
        Formats dicom patient name into a dictionary, see https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_6.2.html#sect_6.2.1.1
        With dict keys: ["last_name", "first_name", "middle_name", "prefix_name", "suffix_name"]

        Args:
           dcm_patient_name (str): Dicom PatientName field = dcm.PatientName
        Returns:
            name_dict (dict): dictionary with keys ["last_name", "first_name", "middle_name", "prefix_name", "suffix_name"]
        """

        name_list = dcm_patient_name.split("^")
        name_list_keys = ["last_name", "first_name", "middle_name", "prefix_name", "suffix_name"]
        name_dict = dict(zip(name_list_keys, name_list))
        return name_dict

    def set_dcm_patient_name(self) -> None:
        """
        Pass to read_dcm_patient_name to extract the dcm.PatientName attribute into individual components and set them to this class
        """
        dcm_patient_name = str(self.dcm.PatientName)
        name_dict = self.read_dcm_patient_name(dcm_patient_name)
        for key, value in name_dict.items():
            self.__setattr__(key, value)
        return

    def read_rd_properties(self) -> dict:
        """
        Extract dicom RD info and output a dictionary with keys for ["referenced_rtplan_uid", "dose_summation_type", "referenced_beam_number"].
        Function was written to create warnings for possibility of having multiple referenced plan sequences/fraction group/beam sequences

        Returns:
            Dict[str, str]: output dictionary with keys for ["referenced_rtplan_uid", "dose_summation_type", "referenced_beam_number"]

        TODO
            - Possibly shorten this code to handle getting the required information.
        """

        dcm = self.dcm

        # Read referenced RTPlan SOPInstanceUID, send a warning if there are multiple referenced plan sequences
        num_ref_rtp = len(dcm.ReferencedRTPlanSequence)
        if num_ref_rtp != 1:
            warnings.warn(
                "RTDose {RTDose!r} contains {num_ref_rtp!r} referenced RTPlanSequences.  Reading first index only.".format(
                    RTDose=dcm.filename, num_ref_rtp=num_ref_rtp
                )
            )

        ref_plan_uid = dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID

        # Dose Summation Type, "PLAN" or "BEAM"
        summation_type = dcm.DoseSummationType

        # Read referenced beam number, all this code because there could be multiple referenced fraction group sequences or beam sequences
        if summation_type == "BEAM":
            num_ref_fgs = len(dcm.ReferencedRTPlanSequence[0].ReferencedFractionGroupSequence)
            if num_ref_fgs != 1:
                warnings.warn(
                    "RTDose {RTDose!r} contains {num_ref_fgs!r} referenced FractionGroupSequences.  Reading first index only.".format(
                        RTDose=dcm.filename, num_ref_fgs=num_ref_fgs
                    )
                )
            num_ref_rbs = len(
                dcm.ReferencedRTPlanSequence[0]
                .ReferencedFractionGroupSequence[0]
                .ReferencedBeamSequence
            )
            if num_ref_rbs != 1:
                warnings.warn(
                    "RTDose {RTDose!r} contains {num_ref_rbs!r} referenced Beam Sequences.  Reading first index only.".format(
                        RTDose=dcm.filename, num_ref_rbs=num_ref_rbs
                    )
                )
            ref_beam_number = (
                dcm.ReferencedRTPlanSequence[0]
                .ReferencedFractionGroupSequence[0]
                .ReferencedBeamSequence[0]
                .ReferencedBeamNumber
            )
        elif summation_type == "PLAN":
            ref_beam_number = None

        rd_info_dict = {
            "referenced_rtplan_uid": ref_plan_uid,
            "dose_summation_type": summation_type,
            "referenced_beam_number": ref_beam_number,
        }

        return rd_info_dict

    def read_rp_properties(self) -> dict:
        """
        Extract dicom RP info and output a dictionary with keys for ["plan_name", "beam_sequence"].

        Returns:
            output_dict (dict): output dictionary with keys for ["plan_name", "beam_sequence"]

        """

        dcm = self.dcm

        # Extract Plan Label
        plan_name = dcm.RTPlanLabel

        # Extract Beam Sequence information
        beam_sequence_dict = {}
        for beam_sequence in dcm.BeamSequence:
            beam_sequence_dict[beam_sequence.BeamNumber] = {
                "beam_number": beam_sequence.BeamNumber,
                "beam_name": beam_sequence.BeamName,
                "beam_description": beam_sequence.BeamDescription,
            }

        return {"plan_name": plan_name, "beam_sequence": beam_sequence_dict}

    def set_rd_rp_properties(self) -> None:
        if self.modality == "RTDOSE":
            rd_dict_info = self.read_rd_properties()
            for key, value in rd_dict_info.items():
                self.__setattr__(key, value)

        if self.modality == "RTPLAN":
            rp_dict_info = self.read_rp_properties()
            for key, value in rp_dict_info.items():
                self.__setattr__(key, value)

    def set_beam_properties(self, DicomNamer_list: list) -> str:
        if self.modality == "RTDOSE" and self.dose_summation_type == "BEAM":
            relevant_RP_list = [
                dcm for dcm in DicomNamer_list if dcm.SOPInstanceUID == self.referenced_rtplan_uid
            ]
            if len(relevant_RP_list) == 0:
                return "no RP plan found"

            if len(relevant_RP_list) > 1:
                logging.warning(
                    "More than one referenced RP found, reading beam names from first one"
                )

            RP = relevant_RP_list[0]
            try:
                RP_beam_sequence = RP.beam_sequence
                logging.info(RP_beam_sequence)
                self.beam_name = RP_beam_sequence[self.referenced_beam_number]["beam_name"]
                self.beam_description = RP_beam_sequence[self.referenced_beam_number][
                    "beam_description"
                ]
                return "success"
            except:
                logging.warning(
                    f"Unable to set beam_name and beam_description for {self.file_path} using {RP.file_path}"
                )
                return "fail"
        return "pass"

    def get_new_name(self) -> str:
        if self.modality == "RTPLAN":
            new_filename = self.RP_filename_placeholder.format(plan_name=self.plan_name)

        if self.modality == "RTDOSE" and self.dose_summation_type == "PLAN":
            new_filename = self.RD_sum_filename_placeholder.format(plan_name=self.plan_name)

        if self.modality == "RTDOSE" and self.dose_summation_type == "BEAM":
            new_filename = self.RD_beam_filename_placeholder.format(
                beam_name=self.beam_name, beam_description=self.beam_description
            )

        new_filename = slugify(new_filename) + ".dcm"
        return new_filename

    def save_as_new_name(self) -> str:
        new_filename = self.get_new_name()
        new_filepath = os.path.join(self.root_dir, new_filename)
        file_renamer(self.file_path, new_filepath, delete=False)
        return new_filepath


# Dicom RP and RP file renaming
def rename_dicom_RD_RP(os_path: str, new_patient_name: str = "", new_patient_id: str = "") -> None:
    """
    Helper function for renaming exported dicom RD and RP from RayStation.
    Default filenames used involve UID, this function renames them to beam name & description.
    Takes input os.path for processing, optional inputs for rewriting patient name and ID
    """

    # Read dicom files in directory
    filename_wildcard = "*.dcm"
    filename_list = glob.glob(os.path.join(os_path, filename_wildcard))

    dicom_read_file_typed: Callable[[str], dicom.dataset.FileDataset] = dicom.read_file

    # Read files, pass into DicomNamer class
    dicomnamer_list = [
        DicomNamer(dicom_read_file_typed(file), new_patient_name, new_patient_id)
        for file in filename_list
    ]

    # Set beam sequence properties for RTDose with Beam doses
    results_set_beam_properties = [
        dcm.set_beam_properties(dicomnamer_list) for dcm in dicomnamer_list
    ]

    # Resave all dicom files with new names
    results_save_as_new = [dcm.save_as_new_name() for dcm in dicomnamer_list]

    return


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
        return str(self.Title)

    def get_dicomscp_dict(self) -> dict:
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

    def update_with_kwargs(self, **kwargs):
        # Update ExportFolderPath
        if self.ExportFolderPath:
            self.ExportFolderPath = self.ExportFolderPath.format(**kwargs)
        return self

    def generate_xaml_attribute_dict(self):
        """
        Generates dictionary with key = class attribute name and dictionary of xaml related values

        Returns:
            _type_: _description_
        """

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

    def get_export_kwargs(self):
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
    ):
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

    def handle_result(self, result):
        try:
            json_string = json.loads(str(result))
            comment_block: str = json_string["Comment"]
            warnings: list[str] = json_string["Warnings"]
            notifications: list[str] = json_string["Notifications"]

            warnings_block = "\n".join(warnings)
            notifications_block = "\n".join(notifications)

            result = f"Comment:\n{comment_block}\n\nWarnings:\n{warnings_block}\n\nNotifications:\n{notifications_block}"

        except ValueError as error:
            logging.info(result)
            # raise_error(f"Error reading completion message.", error)

        return result

    def generate_gui_message(self, success: bool, result=None):
        log_message = ""
        if success:
            status_message = "COMPLETE"
            log_message = f"{self.name} export... COMPLETE\n\n"
        else:
            status_message = "Error"
            log_message = f"{self.name} export... Error\n\n"

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

    def export(self, case: PyScriptObject, examination: PyScriptObject, beam_set: PyScriptObject):  # type: ignore
        attr_was_set = self.set_export_arguments(examination, beam_set)
        if not attr_was_set:
            status_message = "SKIPPED"
            log_message = f"{self.name} export... SKIPPED\n\n"
            print(log_message)
            return status_message, log_message

        export_kwargs = self.get_export_kwargs()

        try:
            print(f"Attempting to export to {self.name}")
            result = case.ScriptableDicomExport(**export_kwargs)
            status_message, log_message = self.generate_gui_message(success=True, result=result)
        except System.InvalidOperationException as error:
            print(f"Attempting to export to {self.name}, ignoring warnings")
            self.handle_log_warnings(error)
            export_kwargs["IgnorePreConditionWarnings"] = True
            result = case.ScriptableDicomExport(**export_kwargs)
            status_message, log_message = self.generate_gui_message(success=True, result=result)
        except Exception as error:
            print(error)
            status_message, log_message = self.generate_gui_message(
                success=False, result=str(error)
            )
            logging.info(f"Export incomplete, {error}")

        return status_message, log_message
