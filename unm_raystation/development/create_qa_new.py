"""
Create a new QA plan for the current beamset

"""

__author__ = "Christopher Hooper, Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "1.0.0"
__license__ = "MIT"


from typing import Dict, Optional

from util_raystation_general import get_current_helper, save_patient

from connect import PyScriptObject


class CreatePatientQA:
    def __init__(self):
        # Load patient, case, beamset data
        self.patient: PyScriptObject = get_current_helper("Patient")
        self.case: PyScriptObject = get_current_helper("Case")
        self.plan: PyScriptObject = get_current_helper("Plan")
        self.beam_set: PyScriptObject = get_current_helper("BeamSet")
        save_patient(self.patient)

        # QA Plan creation parameters
        self.phantom_name: str = "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"
        self.phantom_id: str = "SNC_ArcCheck"
        self.isocenter: Dict[str, float] = {"x": 0, "y": 0.05, "z": 0}
        self.dose_grid: Dict[str, float] = {
            "x": self.beam_set.FractionDose.InDoseGrid.VoxelSize.x,
            "y": self.beam_set.FractionDose.InDoseGrid.VoxelSize.y,
            "z": self.beam_set.FractionDose.InDoseGrid.VoxelSize.z,
        }
        self.GantryAngle: Optional[float] = None
        self.CollimatorAngle: Optional[float] = None
        self.CouchRotationAngle: Optional[float] = 0
        self.ComputeDose: bool = True

    def get_QA_plan_name(self) -> str:
        prefix = "QA"
        i = 0
        while True:
            i += 1
            name = prefix + "_" + str(i)
            name_conflict = any(
                p.BeamSet.DicomPlanLabel == name for p in self.plan.VerificationPlans
            )
            if not name_conflict:
                return name

    def create_qa_plan(self) -> PyScriptObject:
        name = self.get_QA_plan_name()
        self.beam_set.CreateQAPlan(
            PhantomName=self.phantom_name,
            PhantomId=self.phantom_id,
            QAPlanName=name,
            IsoCenter=self.isocenter,
            DoseGrid=self.dose_grid,
            GantryAngle=self.GantryAngle,
            CollimatorAngle=self.CollimatorAngle,
            CouchRotationAngle=self.CouchRotationAngle,
            ComputeDoseWhenPlanIsCreated=self.ComputeDose,
        )

        self.patient.Save()
        num_verification_plans = len(self.plan.VerificationPlans)
        last_plan = self.plan.VerificationPlans[
            num_verification_plans - 1
        ]  # self.plan.VerificationPlans[-1] does not work because it has to call RayStation API
        return last_plan


if __name__ == "__main__":
    create_patient_instance = CreatePatientQA()
    create_patient_instance.create_qa_plan()
