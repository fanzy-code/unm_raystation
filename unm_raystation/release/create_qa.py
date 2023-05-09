from connect import *

# Load patient and case data
try:
    patient = get_current("Patient")
except SystemError:
    raise IOError("No plan loaded.")

try:
    case = get_current("Case")
except SystemError:
    raise IOError("No plan loaded.")

try:
    plan = get_current("Plan")
except SystemError:
    raise IOError("No plan loaded.")
# total_dose = plan.TreatmentCourse.TotalDose

try:
    beam_set = get_current("BeamSet")
except SystemError:
    raise IOError("No beam set loaded.")
# fraction_dose = beam_set.FractionDose

# Determine unique QA plan name
name = "QA"
prefix = "QA"
name_conflict = False
if len(list(plan.VerificationPlans)) > 0:
    for p in plan.VerificationPlans:
        if p.BeamSet.DicomPlanLabel == name:
            name_conflict = True
    if name_conflict:
        i = 0
        while True:
            i += 1
            name = prefix + "" + str(i)
            available = True
            for p in plan.VerificationPlans:
                if p.BeamSet.DicomPlanLabel == name:
                    available = False
            if available:
                break

# Dose Grid
# resolution = beam_set.FractionDose.InDoseGrid.VoxelSize

xsize = beam_set.FractionDose.InDoseGrid.VoxelSize.x
ysize = beam_set.FractionDose.InDoseGrid.VoxelSize.y
zsize = beam_set.FractionDose.InDoseGrid.VoxelSize.z


# Create QA Plan:

beam_set.CreateQAPlan(
    PhantomName="SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom",
    PhantomId="SNC_ArcCheck",
    QAPlanName=name,
    IsoCenter={"x": 0, "y": 0.05, "z": 0},
    DoseGrid={"x": xsize, "y": ysize, "z": zsize},
    GantryAngle=None,
    CollimatorAngle=None,
    CouchRotationAngle=0,
    ComputeDoseWhenPlanIsCreated=True,
)

# Save:
patient.Save()
last_plan = len(list(plan.VerificationPlans)) - 1
