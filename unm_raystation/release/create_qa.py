from connect import *
beam_set = get_current("BeamSet")

beam_set.CreateQAPlan(
	QAPlanName = 
	PhantomName = "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"
	PhantomId = 'SNC_ArcCheck'
	Isocenter = {'x':0, 'y': 0.05, 'z': 0}
	DoseGrid = {beam_set.FractionDose.InDoseGrid.VoxelSize}
	GantryAngle = None
	CollimatorAngle = None
	CouchRotationAngle = 0
	ComputeDoseWhenPlanIsCreated = True
)