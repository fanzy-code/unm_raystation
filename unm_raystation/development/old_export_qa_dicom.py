""" 
    export_patient_dicom

    exports patient dicom to multiple locations for plan processing


    Functional for RayStation 11 & Python 3.8

    
    To Do:
    - Load patient, case, beamset data should be rewritten into a general helper function, with error logging
    - Patient saving should be rewritten outside, with proper error logging
"""

__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "0.1.0"
__license__ = "MIT"

# Import Libraries
import logging

from connect import get_current
from System.IO import InvalidDataException


def main(Patient, Case, BeamSet):
    # case.ScriptableDicomExport(
    #     ExportFolderPath = path.join(getcwd(), patient.Name),
    #     Examinations = [e.Name for e in case.Examinations],
    #     RtStructureSetsForExaminations = [e.Name for e in case.Examinations],
    #     IgnorePreConditionWarnings = True
    # )

    # case.ScriptableDicomExport(
    #     ExportFolderPath = path.join(getcwd(), patient.Name),
    #     Examinations = [e.Name for e in case.Examinations],
    #     RtStructureSetsForExaminations = [e.Name for e in case.Examinations],
    #     IgnorePreConditionWarnings = True
    # )

    print("hello world")


if __name__ == "__main__":
    # Load patient, case, beamset data:
    try:
        patient = get_current("Patient")
    except InvalidDataException:
        logging.exception("message")
        raise Exception("No patient loaded.")
    try:
        case = get_current("Case")
    except InvalidDataException:
        raise Exception("No case loaded.")
    try:
        beam_set = get_current("BeamSet")
    except InvalidDataException:
        raise Exception("No BeamSet loaded.")

    # Check if saving is needed
    if patient.ModificationInfo == None:
        try:
            patient.Save()
        except Exception as error:
            print(error)
            raise

    main(Patient=patient, Case=case, BeamSet=beam_set)
