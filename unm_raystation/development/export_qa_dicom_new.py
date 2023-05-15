""" 
export_qa_dicom

Adapted from RayStation example script Example_06_DICOM_QA_export.py, 
this script exports all QA plans for phantom_name to base_qa_directory and performs renaming of
RP and RD files to something more meaningful.  

TODO:
- Import paths from fixture instead of defining here

Features To Do:
- Remove hard coding of phantom_name by:
    Allowing user to select the verification plan to export (this is necessary because get_current does not support get VerificationPlan,
    workaround by listing all verification plans associated with active beam set and prompt user to select one for export if necessary (>1)
- Check for final dose


"""

__author__ = "Michael Fan and Jorge Zavala"
__contact__ = "mfan1@unmmg.org"
__version__ = "1.0.0"
__license__ = "MIT"

import datetime
import json
from typing import List, Literal

from util_file_operations import (
    clean_working_directory_dcm,
    create_sub_directory,
    rename_dicom_RD_RP,
)
from util_raystation_general import (
    get_current_helper,
    raise_error,
    save_patient,
    slugify,
)

from connect import PyScriptObject


class ExportPatientQA:
    def __init__(self):
        self.phantom_name: str = "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"
        self.base_qa_directory: str = (
            "//health/hsc_departments/crtc/DEPS/PHYSICS/PatientQA/IMRT QA"
        )
        self.sub_directory_format: str = (
            "{machine_name}/{year}/{month}/{patient_name}/{qa_plan_name}"
        )
        self.archive_directory: bool = False

        # Load patient, case, beamset data
        self.patient: PyScriptObject = get_current_helper("Patient")
        self.case: PyScriptObject = get_current_helper("Case")
        self.plan: PyScriptObject = get_current_helper("Plan")
        self.beam_set: PyScriptObject = get_current_helper("BeamSet")

        save_patient(self.patient)

        self.verification_plans: List[PyScriptObject] = self.plan.VerificationPlans

    def get_sub_directory_path(self, verification_plan: PyScriptObject) -> str:
        machine_name = slugify(verification_plan.BeamSet.MachineReference.MachineName)
        year = str(datetime.datetime.now().year)
        month = "{:02d}_{month}".format(
            datetime.datetime.now().month, month=datetime.datetime.now().strftime("%B")
        )
        patient_name = slugify(
            "{name}_{patient_id}".format(name=self.patient.Name, patient_id=self.patient.PatientID)
        )
        qa_plan_name = slugify(
            "{qa_plan_name}".format(qa_plan_name=verification_plan.BeamSet.DicomPlanLabel)
        )

        sub_directory = self.sub_directory_format.format(
            machine_name=machine_name,
            year=year,
            month=month,
            patient_name=patient_name,
            qa_plan_name=qa_plan_name,
        )

        return sub_directory

    def get_relevant_verification_plans(self) -> List[PyScriptObject]:
        """
        This function was created because get_current does not support get VerificationPlan.
        So the workaround was to get a list of all verification plans associated with the active beam set's DicomPlanLabel
        and PhantomName of interest.
        """

        # Find relevant verification plans for current selected beam set
        relevant_verification_plans = []
        for verification_plan in self.verification_plans:
            if (
                verification_plan.OfRadiationSet.DicomPlanLabel == self.beam_set.DicomPlanLabel
            ) and (
                verification_plan.PhantomStudy.PhantomName == self.phantom_name
            ):  # Find verification plans which match current (active) beam set
                relevant_verification_plans.append(verification_plan)

        if len(relevant_verification_plans) == 0:
            raise_error("Found no verification plan to export.", ValueError, terminate=True)

        return relevant_verification_plans

    def LogWarning(self, error) -> None:
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

    def LogCompleted(self, result) -> None:
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

    def export_qa_plan(self, verification_plan_setting: Literal["all", "last"] = "all") -> None:
        if verification_plan_setting == "all":
            relevant_verification_plans = self.get_relevant_verification_plans()
        elif verification_plan_setting == "last":
            num_verification_plans = len(self.plan.VerificationPlans)
            relevant_verification_plans = [
                self.verification_plans[num_verification_plans - 1]
            ]  # self.plan.VerificationPlans[-1] does not work because it has to call RayStation API
        else:
            raise ValueError("verification_plan_setting must be either 'all' or 'last'.")

        for verification_plan in relevant_verification_plans:
            try:
                # Create subfolder directory
                path = create_sub_directory(
                    self.base_qa_directory, self.get_sub_directory_path(verification_plan)
                )

                # Clean the working directory of .dcm files
                clean_working_directory_dcm(path, self.archive_directory)

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
                processing = rename_dicom_RD_RP(
                    os_path=path,
                    new_patient_name=self.patient.Name,
                    new_patient_id=self.patient.PatientID,
                )

                self.LogCompleted(result)
            except SystemError as error:
                # The script failed due to warnings or errors.
                self.LogWarning(error)

        return


if __name__ == "__main__":
    export_patient_qa = ExportPatientQA()
    export_patient_qa.export_qa_plan(verification_plan_setting="all")
