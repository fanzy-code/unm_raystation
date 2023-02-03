""" 
    Installation:
    Prints per beam dose to each POI for every beam set.  

    To run, copy and paste the code into console

    To do:
        - Create a GUI
"""

__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "0.1.0"
__license__ = "MIT"

for beam_set in plan.BeamSets:  # type: ignore
    print(beam_set.DicomPlanLabel)
    structure_set = beam_set.GetStructureSet()
    FoR = beam_set.FrameOfReference

    point_names = []
    points = []
    for point in structure_set.PoiGeometries:
        if point.Point != None:
            point_names.append(point.OfPoi.Name)
            points.append(point.Point)

    # Verifying the output for total dose:
    total_dose = beam_set.FractionDose.InterpolateDoseInPoints(
        Points=points, PointsFrameOfReference=FoR
    )
    row_format_total = "{:<25} {:<25} " + "{:<25} " * (len(point_names))
    print(row_format_total.format("", "Points", *point_names))  # Printing headers
    print(row_format_total.format("", "Total Dose (cGy)", *total_dose.tolist()))
    print("\n")

    # Print dose per field to each point
    row_format_per_beam = "{:<25} {:<25} " + "{:<25} " * (len(point_names))
    header = row_format_per_beam.format("Beam Name", "Beam Description", *point_names)
    print(header)
    for beam_dose in beam_set.FractionDose.BeamDoses:
        beam_doses = beam_dose.InterpolateDoseInPoints(Points=points, PointsFrameOfReference=FoR)
        row = row_format_per_beam.format(
            beam_dose.ForBeam.Name, beam_dose.ForBeam.Description, *beam_doses
        )
        print(row)
    print("\n")
