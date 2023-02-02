""" export qa dicom

    Adapted from RayStation example script Example_06_DICOM_QA_export.py, 
    this script exports all QA plans for phantom_name to base_qa_directory and performs renaming of
    RP and RD files to something more meaningful.  

    Quality improvements to Do:
    - Import paths from fixture instead of defining here
    - separate functions out of main and use python boiler plate = if __name__ == '__main__':
    - unit testing for functions

    Features To Do:
    - Remove hard coding of phantom_name by:
     Allowing user to select the verification plan to export (this is necessary because get_current does not support get VerificationPlan,
     workaround by listing all verification plans associated with active beam set and prompt user to select one for export if necessary (>1)
    - Check for final dose

    RELEASE NOTES:
    Turn on SNC_ArcCheck Phantom instead of ICP
    """

__author__ = "Michael Fan and Jorge Zavala"
__contact__ = "mfan1@unmmg.org"
__version__ = "0.2.1"
__license__ = "MIT"

import datetime
import glob
import json
import os

import rs_utils  # type: ignore
from connect import *  # type: ignore

# Define paths
# phantom_name = 'ICP_Virtual Phantom'
phantom_name = "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"
base_qa_directory = "//health/hsc_departments/crtc/DEPS/PHYSICS/PatientQA/IMRT QA"
sub_directory_format = "{machine_name}/{year}/{month}/{patient_name}/{qa_plan_name}"
archive_directory = False


# Example on how to read the JSON error string.
def LogWarning(error):
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
    except ValueError:
        print("Error occurred. Could not export.")


# The error was likely due to a blocking warning, and the details should be stated
# in the execution log.
# This prints the successful result log in an ordered way.
def LogCompleted(result):
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
    except ValueError:
        print("Error reading completion messages.")


# Load patient, case, beamset data
patient = rs_utils.get_current_helper("Patient")
case = rs_utils.get_current_helper("Case")
plan = rs_utils.get_current_helper("Plan")
beam_set = rs_utils.get_current_helper("BeamSet")

# Check for saving
rs_utils.save_patient(patient)

# Get the verification plans. This gets all verification plans on a plan.
verification_plans = plan.VerificationPlans

# Find relevant verification plans (ArcCheck) for current selected beam set
relevant_verification_plans = []
for verification_plan in verification_plans:
    if (
        verification_plan.OfRadiationSet.DicomPlanLabel == beam_set.DicomPlanLabel
    ):  # Find verification plans which match current (active) beam set
        if verification_plan.PhantomStudy.PhantomName == phantom_name:
            relevant_verification_plans.append(verification_plan)

if len(relevant_verification_plans) == 0:
    raise Exception("Found no verification plan to export.")

for verification_plan in relevant_verification_plans:
    try:
        # Create desired subfolder directory
        machine_name = verification_plan.BeamSet.MachineReference.MachineName
        year = str(datetime.datetime.now().year)
        month = "{:02d}_{month}".format(
            datetime.datetime.now().month, month=datetime.datetime.now().strftime("%B")
        )
        patient_name = rs_utils.slugify(
            "{name}_{patient_id}".format(name=patient.Name, patient_id=patient.PatientID)
        )
        qa_plan_name = rs_utils.slugify(
            "{qa_plan_name}".format(qa_plan_name=verification_plan.BeamSet.DicomPlanLabel)
        )
        sub_directory = sub_directory_format.format(
            machine_name=machine_name,
            year=year,
            month=month,
            patient_name=patient_name,
            qa_plan_name=qa_plan_name,
        )
        path = os.path.join(base_qa_directory, sub_directory)
        os.makedirs(path, exist_ok=True)

        # Clean the working directory of .dcm files
        filename_wildcard = "*.dcm"
        old_filename_list = glob.glob(os.path.join(path, filename_wildcard))
        for old_file in old_filename_list:
            if archive_directory == False:
                os.remove(old_file)
            elif archive_directory == True:
                new_path = rs_utils.file_archive(old_file)

        # Export the verification plan
        result = verification_plan.ScriptableQADicomExport(
            ExportFolderPath=path,
            QaPlanIdentity="Phantom",
            ExportExamination=False,  # CT
            ExportExaminationStructureSet=False,  # RT Structure Set
            ExportBeamSet=True,  # RT Plan
            ExportBeamSetDose=True,  # RT Dose Sum
            ExportBeamSetBeamDose=True,  # RT Dose per beam
            IgnorePreConditionWarnings=False,
        )

        # Rename the RD and RP files in the folder
        processing = rs_utils.rename_dicom_RD_RP(
            os_path=path, new_patient_name=patient.Name, new_patient_id=patient.PatientID
        )

        # It is important to read the result event if the script was successful.
        # This gives the user a chance to see possible warnings that were ignored, if for
        # example the IgnorePreConditionWarnings was set to True by mistake. The result
        # also contains other notifications the user should read.
        LogCompleted(result)
    except SystemError as error:
        # The script failed due to warnings or errors.
        LogWarning(error)

        print("\nTry to export again with IgnorePreConditionWarnings=True\n")
