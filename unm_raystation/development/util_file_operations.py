"""
Contain utility functions for file operations.
"""
import datetime
import glob
import logging
import os
import shutil
import warnings
from pathlib import Path
from typing import Callable

import pydicom as dicom
from pydicom.dataset import FileDataset
from util_raystation_general import slugify


def archive_file(src_path: str) -> str:
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


def clean_working_directory_dcm(path: str, archive_directory: bool = False) -> None:
    """
    Clean the working directory of .dcm files by deleting or archiving them.

    Args:
        path (str): _description_
        archive_directory (bool, optional): _description_. Defaults to False.
    """
    filename_wildcard = "*.dcm"
    old_filename_list = glob.glob(os.path.join(path, filename_wildcard))
    for old_file in old_filename_list:
        if archive_directory == False:
            os.remove(old_file)
        elif archive_directory == True:
            new_path = archive_file(old_file)
    return


def create_sub_directory(base_qa_directory: str, sub_directory: str) -> str:
    """
    Helper function to create a subdirectory in the base_qa_directory.
    If the subdirectory already exists, it will not be recreated.
    Returns the path to the subdirectory.

    Args:
        base_qa_directory (str): _description_
        sub_directory (str): _description_

    Returns:
        str: _description_
    """
    path = os.path.join(base_qa_directory, sub_directory)
    os.makedirs(path, exist_ok=True)
    return path


def rename_file(src_path: str, dst_path: str, delete: bool = True) -> str:
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
            new_path = archive_file(src_path)
            logging.info(f"Duplicate found, archived destination file to: {new_path}")

    os.rename(src_path, dst_path)
    return f"Renamed {src_path} to {dst_path}"


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


class DicomNamer:
    """
    Class to extract data from Dicom RP and RD files for renaming purposes
    """

    # Filename placeholder strings
    RD_sum_filename_placeholder = "RD_Sum_{plan_name}"
    RD_beam_filename_placeholder = "RD_{beam_name}_{beam_description}"
    RP_filename_placeholder = "RP_{plan_name}"

    def __init__(self, dcm: FileDataset, new_patient_name: str = "", new_patient_id: str = ""):
        if not isinstance(dcm, dicom.dataset.FileDataset):
            raise TypeError("dcm must be an instance of pydicom.dataset.FileDataset")

        self.dcm: FileDataset = dcm
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
        rename_file(self.file_path, new_filepath, delete=False)
        return new_filepath


if __name__ == "__main__":
    from util_raystation_general import raise_error

    test_error = "This script is not meant to be run directly!  This script contains helper functions for other scripts."
    test_exception_message = Exception
    raise_error(test_error, test_exception_message)
