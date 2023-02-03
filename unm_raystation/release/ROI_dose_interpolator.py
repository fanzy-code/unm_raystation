""" 
    Prints per beam dose to each POI active beam set.

    There are two sets of code, one for plans in treatment planning and another for verification plans  

    To run, copy and paste the code into console

    To do:
        - Create a GUI
"""

__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "0.1.0"
__license__ = "MIT"

### Print per beam dose for ROI in active beam_set
roi_name = "SNC125c"
dose_type = "Average"

beam_set = get_current("BeamSet")  # type: ignore
result = {}
structure_set = beam_set.GetStructureSet()
structure_set.RoiGeometries[roi_name]
for beam_dose in beam_set.FractionDose.BeamDoses:
    average = beam_dose.GetDoseStatistic(RoiName=roi_name, DoseType=dose_type)
    result[beam_dose.ForBeam.Name] = average
# Results are unformatted, sorry
print(result)

### Print per beam dose for ROI in verification plan
phantom_name = "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"
roi_name = "SNC125c"
dose_type = "Average"

beam_set = get_current("BeamSet")  # type: ignore
result = {}
for v_plan in plan.VerificationPlans:  # type: ignore
    if v_plan.OfRadiationSet.DicomPlanLabel == beam_set.DicomPlanLabel:
        if v_plan.PhantomStudy.PhantomName == phantom_name:
            beam_doses_to_roi = {}
            for beam_dose in v_plan.BeamSet.FractionDose.BeamDoses:
                average = beam_dose.GetDoseStatistic(RoiName=roi_name, DoseType=dose_type)
                beam_doses_to_roi[beam_dose.ForBeam.Name] = average
            result[v_plan.OfRadiationSet.DicomPlanLabel] = beam_doses_to_roi

# Results are unformatted, sorry
print(result)
