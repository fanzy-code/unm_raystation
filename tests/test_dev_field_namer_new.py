from unittest.mock import MagicMock, Mock

import pytest

from unm_raystation.development.field_namer_new import *


@pytest.fixture
def mock_patient():
    patient = Mock()
    case1 = MagicMock()
    case2 = MagicMock()
    plan1 = MagicMock()
    plan2 = MagicMock()
    beamset1 = MagicMock()
    beamset2 = MagicMock()

    # Treatment Beam objects
    beam1 = MagicMock()
    beam1.Name = "Beam1"

    beam2 = MagicMock()
    beam2.Name = "Beam2"

    beam3 = MagicMock()
    beam3.Name = "Beam3"

    beam4 = MagicMock()
    beam4.Name = "Beam4"

    # PatientSetup
    PatientSetup = MagicMock()

    # Setup Beams
    setupbeam1 = MagicMock()
    setupbeam1.Name = "SetupBeam1"

    setupbeam2 = MagicMock()
    setupbeam2.Name = "SetupBeam2"

    setupbeam3 = MagicMock()
    setupbeam3.Name = "SetupBeam3"

    setupbeam4 = MagicMock()
    setupbeam4.Name = "SetupBeam4"

    # Set up case 1 with beamset 1
    case1.TreatmentPlans = [plan1]
    plan1.BeamSets = [beamset1]
    beamset1.UniqueId = "1"
    beamset1.Beams = [beam1, beam2]
    beamset1.PatientSetup = PatientSetup
    beamset1.PatientSetup.SetupBeams = [setupbeam1, setupbeam2]

    # Set up case 2 with beamset 2
    case2.TreatmentPlans = [plan2]
    plan2.BeamSets = [beamset2]
    beamset2.UniqueId = "2"
    beamset2.Beams = [beam3, beam4]
    beamset2.PatientSetup = PatientSetup
    beamset2.PatientSetup.SetupBeams = [setupbeam3, setupbeam4]

    patient.Cases = [case1, case2]

    return patient


@pytest.fixture
def patient_wrapper(mock_patient):
    # Initialize PatientWrapper with mock patient and beamset
    beamset = MagicMock()
    beamset.UniqueId = "1"
    return PatientWrapper(mock_patient, beamset)


def test_get_all_beam_names(patient_wrapper):
    # Test get_all_beam_names for treatment beams only
    assert patient_wrapper.get_all_beam_names("Treatment") == ["Beam3", "Beam4"]

    # Test get_all_beam_names for setup beams only
    assert patient_wrapper.get_all_beam_names("Setup") == [
        "SetupBeam3",
        "SetupBeam4",
    ]
