import asyncio
import os
import tempfile
from unittest.mock import Mock

import pytest

from unm_raystation.development.export_qa_dicom_new import *


@pytest.fixture
def mock_get_current_helper():
    # Create a mock function that returns dummy patient, case, beamset, and plan data
    patient = Mock()
    case = Mock()
    plan = Mock()
    beam_set = Mock()
    mock_func = Mock(side_effect=[patient, case, beam_set, plan])
    return mock_func


def test_export_qa_instantiate(mock_get_current_helper):
    export_patient_instance = ExportPatientQA()
    assert export_patient_instance.phantom_name == "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"


# @pytest.fixture
# def temp_dir():
#     with tempfile.TemporaryDirectory() as tmpdir:
#         yield tmpdir


# @pytest.mark.asyncio
# @pytest.mark.parametrize("verification_plan_setting", ["all", "last"])
# def test_export_qa(export_qa, temp_dir, verification_plan_setting):
#     export_qa.base_qa_directory = temp_dir
#     export_qa.export_qa(verification_plan_setting)

#     relevant_verification_plans = export_qa.get_relevant_verification_plans()

#     for verification_plan in relevant_verification_plans:
#         sub_directory = export_qa.get_sub_directory_path(verification_plan)

#         expected_dir = os.path.join(temp_dir, sub_directory)
#         assert os.path.isdir(expected_dir)

#         for filename in os.listdir(expected_dir):
#             old_path = os.path.join(expected_dir, filename)
#             new_path = os.path.join(expected_dir, export_qa.get_new_filename(filename))

#             assert os.path.isfile(new_path)
#             assert not os.path.isfile(old_path)
