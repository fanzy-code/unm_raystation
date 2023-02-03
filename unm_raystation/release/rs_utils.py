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
__version__ = "0.1.1"
__license__ = "MIT"

import datetime
import glob
import logging
import os
import re
import shutil

# Functions
import sys
import unicodedata
import warnings

import pydicom as dicom
from connect import PyScriptObject, get_current  # type: ignore


def raise_error(error_message: str, rs_exception_error) -> None:
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
        input (str): Supported inputs are "Patient", "Case", "Plan", "BeamSet", "Examination", "PatientDB", "MachineDB"

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


# Wrapper function for Patient.Save() with error loggin
def save_patient(patient):
    """
    Helper function for Patient.Save() function from Raystation.
    Patient class required as input, checks if modifications are made and saves the patient if so.
    """
    if patient.ModificationInfo == None:
        try:
            patient.Save()
        except Exception as error:
            logging.exception(error)
            error_message = "Unable to save patient."
            raise_error(error_message=error_message, exception_error=error)


# Sanitize URLs and Filenames
def slugify(value, allow_unicode=False):
    """
    Django's function for sanitizing filenames and URLs.  Gold standard for making
    input strings URL and filename friendly.

    Modified to keep case instead of making everything lower case.

    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[-\s]+", "-", value).strip("-_")


# File Archive function for storing
def file_archive(src_path):
    """
    Helper function for archiving files.
    Takes input src_path for filepath.  Archive files in archive sub directory.
    """
    # Make sub-directory Archive if needed
    base_directory = os.path.dirname(src_path)
    sub_directory = os.path.join(base_directory, "Archive")
    os.makedirs(sub_directory, exist_ok=True)

    # Create new base filename for copying destination
    now = datetime.datetime.now().strftime("_%Y-%m-%d_%H-%M-%S")
    file_basename = os.path.basename(src_path)
    new_file_basename = os.path.splitext(file_basename)[0] + now

    # Full path to destination
    new_path = os.path.join(sub_directory, new_file_basename + ".dcm")
    shutil.move(src_path, new_path)

    return new_path


# File handling function for renaming, handles duplications
def file_renamer(src_path, dst_path, delete=True):
    """
    Helper function for renaming files.
    delete=True will remove originals if destination file path already exists.
    delete=False will pass to file_archive function for archiving
    """
    if os.path.exists(dst_path):
        if delete == True:
            os.remove(dst_path)
            return "Duplicate found, deleted original file: {dst_path}".format(dst_path=dst_path)

        elif delete == False:
            new_path = file_archive(src_path)
            return "Duplicate found, archived original as {new_path}".format(new_path=new_path)

    os.rename(src_path, dst_path)
    return "No duplicates found, renamed {src_path} to {dst_path}".format(
        src_path=src_path, dst_path=dst_path
    )


# Dicom RP and RP file renaming
def rename_dicom_RD_RP(os_path, new_patient_name=None, new_patient_id=None):
    """
    Helper function for renaming exported dicom RD and RP from RayStation.
    Default filenames used involve UID, this function renames them to beam name & description.
    Takes input os.path for processing, optional inputs for rewriting patient name and ID
    """

    # File name formatting string
    RD_sum_filename_format = "RD_Sum_{plan_name}"
    RD_beam_filename_format = "RD_{beam_name}_{beam_description}"
    RP_filename_format = "RP_{plan_name}"

    # Read dicom files in directory
    filename_wildcard = "*.dcm"
    filename_list = glob.glob(os.path.join(os_path, filename_wildcard))

    # Initialize output_dictionary
    output_dict = {"RP_files": {}, "RD_files": {}}

    # Read files, sort into RD or RP list
    for file in filename_list:
        # Read dicom file
        try:
            dcm = dicom.read_file(file)

            save_as = False
            # Rewrite Patient Name if supplied
            if new_patient_name != None:
                dcm.PatientName = new_patient_name
                save_as = True

            # Rewrite Patient ID if supplied
            if new_patient_id != None:
                dcm.PatientID = new_patient_id
                save_as = True

            # Save new dicom if necessary
            if save_as:
                dcm.save_as(file)

        except Exception as error:
            error_message = "Unable to open {file}".format(file=file)
            raise_error(error_message=error_message, exception_error=error)

        # Extract patient name, see https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_6.2.html#sect_6.2.1.1
        dicom_patient_name = str(dcm.PatientName)
        name_list = dicom_patient_name.split("^")
        name_list_keys = ["last_name", "first_name", "middle_name", "prefix_name", "suffix_name"]
        name_dict = dict(zip(name_list_keys, name_list))

        # Extract patient ID
        try:
            id = dcm.PatientID
        except Exception as error:
            error_message = "Unable to read patient ID."
            raise_error(error_message=error_message, exception_error=error)

        # Parse into dictionary
        dcm_dict = {
            "file_path": file,
            "id": id,
        }

        dcm_dict.update(name_dict)

        if dcm.Modality == "RTDOSE":
            # Read addition RTDose variables

            # Read referenced RTPlan SOPInstanceUID
            num_ref_rtp = len(dcm.ReferencedRTPlanSequence[0])
            if num_ref_rtp != 1:
                warnings.warn(
                    "RTDose {RTDose} contains {num_ref_rtp} referenced RTPlanSequences.  Reading first index only.".format(
                        RTDose=file, num_ref_rtp=num_ref_rtp
                    )
                )

            ref_plan_uid = dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID

            # Dose Summation Type, "PLAN" or "BEAM"
            summation_type = dcm.DoseSummationType

            # Read referenced beam number
            if summation_type == "BEAM":
                num_ref_fgs = len(dcm.ReferencedRTPlanSequence[0].ReferencedFractionGroupSequence)
                if num_ref_fgs != 1:
                    warnings.warn(
                        "RTDose {RTDose} contains {num_ref_fgs} referenced FractionGroupSequences.  Reading first index only.".format(
                            RTDose=file, num_ref_fgs=num_ref_fgs
                        )
                    )
                num_ref_rbs = len(
                    dcm.ReferencedRTPlanSequence[0]
                    .ReferencedFractionGroupSequence[0]
                    .ReferencedBeamSequence
                )
                if num_ref_rbs != 1:
                    warnings.warn(
                        "RTDose {RTDose} contains {num_ref_rbs} referenced Beam Sequences.  Reading first index only.".format(
                            RTDose=file, num_ref_rbs=num_ref_rbs
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

            # Update dcm_dict with additional RTDose entries
            dcm_dict.update(
                {
                    "referenced_rtplan_uid": ref_plan_uid,
                    "dose_summation_type": summation_type,
                    "referenced_beam_number": ref_beam_number,
                }
            )

            output_dict["RD_files"][dcm.SOPInstanceUID] = dcm_dict

        elif dcm.Modality == "RTPLAN":
            # Read additional RTPlan variables

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

            # Update dcm_dict with additional RTPlan entries
            dcm_dict.update({"plan_name": plan_name, "beam_sequence": beam_sequence_dict})

            output_dict["RP_files"][dcm.SOPInstanceUID] = dcm_dict

            # Try renaming the file
            new_RP_base_filename = slugify(RP_filename_format.format(plan_name=plan_name))
            new_RP_filename = new_RP_base_filename + ".dcm"
            new_RP_filepath = os.path.join(os.path.dirname(file), new_RP_filename)
            file_renamer(file, new_RP_filepath, delete=False)

    # Rename RD files
    for rd_uid, rd_dict in output_dict["RD_files"].items():
        # Referenced Plan SOP Instance UID
        ref_plan_uid = rd_dict["referenced_rtplan_uid"]
        rp_dict = output_dict["RP_files"][ref_plan_uid]

        # If RD is for plan sum
        if rd_dict["dose_summation_type"] == "PLAN":
            plan_name = rp_dict["plan_name"]
            dst_base_filename = slugify(RD_sum_filename_format.format(plan_name=plan_name))

        # If RD is for beam dose
        elif rd_dict["dose_summation_type"] == "BEAM":
            # Reference Beam Number & Beam Sequence
            ref_beam_number = rd_dict["referenced_beam_number"]
            beam_sequence = rp_dict["beam_sequence"]

            # Beam Name & Beam Description
            beam_name = beam_sequence[ref_beam_number]["beam_name"]
            beam_description = beam_sequence[ref_beam_number]["beam_description"]

            dst_base_filename = slugify(
                RD_beam_filename_format.format(
                    beam_name=beam_name, beam_description=beam_description
                )
            )

        src_filepath = rd_dict["file_path"]
        dst_filename = dst_base_filename + ".dcm"
        dst_filepath = os.path.join(os.path.dirname(src_filepath), dst_filename)
        file_renamer(src_filepath, dst_filepath, delete=False)
