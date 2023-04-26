import pytest

from definitions import ROOT_DIR
from unm_raystation.development.util_file_operations import *  # type: ignore


def test_get_new_filename():
    test_filename = "foo/bar/file.dcm"  # assume safe input
    now = datetime.datetime.now().strftime("_%Y-%m-%d_%H-%M-%S")
    assert get_new_filename(test_filename) == "file" + now + ".dcm"


@pytest.fixture
def sample_rp_dcm_namer():
    rd_path = ROOT_DIR + "\\tests\\dicom\\RP_Sample.dcm"
    dcm = dicom.read_file(rd_path)
    dcm_namer = DicomNamer(dcm)
    return dcm_namer


@pytest.fixture
def sample_rd_beam_dcm_namer():
    rd_path = ROOT_DIR + "\\tests\\dicom\\RD_Beam_Sample.dcm"
    dcm = dicom.read_file(rd_path)
    dcm_namer = DicomNamer(dcm)
    return dcm_namer


@pytest.fixture
def sample_rd_sum_dcm_namer():
    rd_path = ROOT_DIR + "\\tests\\dicom\\RD_Sum_Sample.dcm"
    dcm = dicom.read_file(rd_path)
    dcm_namer = DicomNamer(dcm)
    return dcm_namer


def test_replace_patient_x(sample_rp_dcm_namer):
    new_patient_name = "new^name"
    new_patient_id = "123"

    change = sample_rp_dcm_namer.replace_patient_attributes(new_patient_name, new_patient_id)
    assert change == True
    assert sample_rp_dcm_namer.dcm.PatientName == new_patient_name
    assert sample_rp_dcm_namer.dcm.PatientID == new_patient_id


def test_read_dcm_patient_name(sample_rp_dcm_namer):
    test_name = "Last^First"
    assert sample_rp_dcm_namer.read_dcm_patient_name(test_name) == {
        "last_name": "Last",
        "first_name": "First",
    }

    test_name = "Last^First^Middle"
    assert sample_rp_dcm_namer.read_dcm_patient_name(test_name) == {
        "last_name": "Last",
        "first_name": "First",
        "middle_name": "Middle",
    }

    test_name = "Last^First^^"
    assert sample_rp_dcm_namer.read_dcm_patient_name(test_name) == {
        "last_name": "Last",
        "first_name": "First",
        "middle_name": "",
        "prefix_name": "",
    }

    test_name = "Last^First^^^"
    assert sample_rp_dcm_namer.read_dcm_patient_name(test_name) == {
        "last_name": "Last",
        "first_name": "First",
        "middle_name": "",
        "prefix_name": "",
        "suffix_name": "",
    }

    test_name = "Last"
    assert sample_rp_dcm_namer.read_dcm_patient_name(test_name) == {
        "last_name": "Last",
    }


def test_set_dcm_patient_name(sample_rp_dcm_namer):
    # Set a more complicated instance of patient name
    sample_rp_dcm_namer.dcm.PatientName = "Last^First^Middle^^"
    dcm_PatientName = str(sample_rp_dcm_namer.dcm.PatientName)
    name_dict = sample_rp_dcm_namer.read_dcm_patient_name(dcm_PatientName)
    sample_rp_dcm_namer.set_dcm_patient_name()
    for key, value in name_dict.items():
        assert sample_rp_dcm_namer.__getattribute__(key) == value


def test_read_rd_properties_one(sample_rd_beam_dcm_namer):
    rd_info_dict = sample_rd_beam_dcm_namer.read_rd_properties()
    assert rd_info_dict == {
        "referenced_rtplan_uid": "1.2.752.243.1.1.20230130114529116.5000.62080",
        "dose_summation_type": "BEAM",
        "referenced_beam_number": "1",
    }


def test_read_rd_properties_two(sample_rd_sum_dcm_namer):
    rd_info_dict = sample_rd_sum_dcm_namer.read_rd_properties()
    assert rd_info_dict == {
        "referenced_rtplan_uid": "1.2.752.243.1.1.20230130114529116.5000.62080",
        "dose_summation_type": "PLAN",
        "referenced_beam_number": None,
    }


def test_set_rd_properties(sample_rd_beam_dcm_namer):
    # Alternatively we can edit the sample_rd_beam_dcm_namer with some new data and make sure the set_rd_rp_properties is working properly
    rd_info_dict = sample_rd_beam_dcm_namer.read_rd_properties()

    assert rd_info_dict == {
        "referenced_rtplan_uid": "1.2.752.243.1.1.20230130114529116.5000.62080",
        "dose_summation_type": "BEAM",
        "referenced_beam_number": "1",
    }

    sample_rd_beam_dcm_namer.set_rd_rp_properties()
    for key, value in rd_info_dict.items():
        assert sample_rd_beam_dcm_namer.__getattribute__(key) == value


def test_set_rp_properties(sample_rp_dcm_namer):
    # Alternatively we can edit the sample_rp_dcm_namer with some new data and make sure the set_rd_rp_properties is working properly
    rp_info_dict = sample_rp_dcm_namer.read_rp_properties()

    sample_rp_dcm_namer.set_rd_rp_properties()
    for key, value in rp_info_dict.items():
        assert sample_rp_dcm_namer.__getattribute__(key) == value


def test_set_beam_properties_and_new_name(
    sample_rd_beam_dcm_namer, sample_rd_sum_dcm_namer, sample_rp_dcm_namer
):
    dicomnamer_list = [sample_rd_beam_dcm_namer, sample_rd_sum_dcm_namer, sample_rp_dcm_namer]
    results_set_beam_properties = [
        dcm.set_beam_properties(dicomnamer_list) for dcm in dicomnamer_list
    ]
    assert results_set_beam_properties == ["success", "pass", "pass"]
    assert sample_rd_beam_dcm_namer.referenced_beam_number == "1"
    assert sample_rd_beam_dcm_namer.beam_name == "A07"
    assert sample_rd_beam_dcm_namer.beam_description == "G181 C0 R Pelvis Bst"
    assert sample_rd_beam_dcm_namer.get_new_name() == "RD_A07_G181-C0-R-Pelvis-Bst.dcm"


def test_get_new_name(sample_rp_dcm_namer):
    assert sample_rp_dcm_namer.get_new_name() == "RP_R-Pelvis-Bst.dcm"
