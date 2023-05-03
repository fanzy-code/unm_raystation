"""
Create a new QA plan for the current beamset

"""


from util_raystation_general import get_current_helper, save_patient


class CreatePatientQA:
    def __init__(self):
        # QA Plan creation parameters
        self.phantom_name = "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"
        self.phantom_id = "SNC_ArcCheck"
        self.isocenter = {"x": 0, "y": 0.05, "z": 0}
        self.dose_grid = {
            "x": 0.25,
            "y": 0.25,
            "z": 0.25,
        }  # plan voxelsize beam_set.FractionDose.InDoseGrid.VoxelSize
        self.GantryAngle = None
        self.CollimatorAngle = None
        self.CouchRotationAngle = 0
        self.ComputeDose = True

        # Load patient, case, beamset data
        self.patient = get_current_helper("Patient")
        self.case = get_current_helper("Case")
        self.plan = get_current_helper("Plan")
        self.beam_set = get_current_helper("BeamSet")
        save_patient(self.patient)

    def get_QA_plan_name(self):
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

    def create_qa_plan(self):
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
