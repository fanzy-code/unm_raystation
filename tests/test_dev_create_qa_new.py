import asyncio
import os
import tempfile
from unittest.mock import Mock

import pytest

from unm_raystation.development.create_qa_new import *


@pytest.fixture
def mock_get_current_helper():
    # Create a mock function that returns dummy patient, case, beamset, and plan data
    patient = Mock()
    case = Mock()
    plan = Mock()
    beam_set = Mock()
    mock_func = Mock(side_effect=[patient, case, beam_set, plan])
    return mock_func


def test_create_qa_instantiate(mock_get_current_helper, monkeypatch):
    monkeypatch.setattr(
        "unm_raystation.development.create_qa_new.get_current_helper",
        mock_get_current_helper,
    )
    export_patient_instance = CreatePatientQA()
    assert export_patient_instance.phantom_name == "SNC_ArcCheck_Virtual 27cm_2cm_Rods Phantom"
