import pytest

from unm_raystation.release.processing_export import (
    AnonymizationSettings,
    DCMExportDestination,
    DicomSCP,
)


def test_DicomSCP_with_Title_only_not_allowed():
    with pytest.raises(ValueError, match="Title "):
        dicomscp = DicomSCP(Title="my_title")


def test_DicomSCP_with_Title_only_allowed():
    dicomscp = DicomSCP(Title="my_title", _allowed_titles=["my_title"])
    assert dicomscp.get_dicomscp_dict() == {"Title": "my_title"}


def test_DicomSCP_with_all_Node_Port_CalledAE_CallingAE_only():
    dicomscp = DicomSCP(
        Node="my_node", Port="my_port", CalledAE="my_called_ae", CallingAE="my_calling_ae"
    )
    assert dicomscp.get_dicomscp_dict() == {
        "Node": "my_node",
        "Port": "my_port",
        "CalledAE": "my_called_ae",
        "CallingAE": "my_calling_ae",
    }


def test_DicomSCP_with_Title_and_Node_Port_CalledAE_CallingAE():
    with pytest.raises(ValueError, match="Both Title"):
        dicomscp = DicomSCP(
            Title="my_title",
            Node="my_node",
            Port="my_port",
            CalledAE="my_called_ae",
            CallingAE="my_calling_ae",
        )


def test_DicomSCP_with_no_Title_and_no_Node_Port_CalledAE_CallingAE():
    with pytest.raises(ValueError, match="Either Title"):
        dicomscp = DicomSCP()


def test_DicomSCP_with_no_Title_and_some_Node_Port_CalledAE_CallingAE():
    with pytest.raises(ValueError, match="Either Title"):
        dicomscp = DicomSCP(Node="my_node")


def test_DicomSCP_with_some_Node_Port_CalledAE_CallingAE_but_not_all():
    with pytest.raises(ValueError, match="Either Title"):
        dicomscp = DicomSCP(Node="my_node", Port="my_port", CalledAE="my_called_ae")


def test_AnonymizationSettings_get_anonymization_settings_dict():
    # Test case for default values
    a = AnonymizationSettings()
    expected = {
        "anonymize": False,
        "AnonymizedName": "anonymizedName",
        "AnonymizedID": "anonymizedID",
        "RetainDates": False,
        "RetainDeviceIdentity": False,
        "RetainInstitutionIdentity": False,
        "RetainUIDS": False,
        "RetainSafePrivateAttributes": False,
    }
    assert a.get_anonymization_settings_dict() == expected

    # Test case for non-default values
    a = AnonymizationSettings(
        anonymize=True,
        AnonymizedName="test_name",
        AnonymizedID="test_id",
        RetainDates=True,
        RetainDeviceIdentity=True,
        RetainInstitutionIdentity=True,
        RetainUIDS=True,
        RetainSafePrivateAttributes=True,
    )
    expected = {
        "anonymize": True,
        "AnonymizedName": "test_name",
        "AnonymizedID": "test_id",
        "RetainDates": True,
        "RetainDeviceIdentity": True,
        "RetainInstitutionIdentity": True,
        "RetainUIDS": True,
        "RetainSafePrivateAttributes": True,
    }
    assert a.get_anonymization_settings_dict() == expected


# def test_DCMExportDestination_init():
#     # Test case for valid input with connection
#     conn = DicomSCP(Title="TestTitle", _allowed_titles=["TestTitle"])
#     a = AnonymizationSettings()
#     d = DCMExportDestination(name="TestName", AnonymizationSettings=a, Connection=conn)
#     assert d.name == "TestName"
#     assert d.AnonymizationSettings == a
#     assert d.Connection == conn
#     assert d.ExportFolderPath is None

#     # Test case for valid input with export folder path
#     a = AnonymizationSettings()
#     d = DCMExportDestination(
#         name="TestName", AnonymizationSettings=a, ExportFolderPath="/path/to/export"
#     )
#     assert d.name == "TestName"
#     assert d.AnonymizationSettings == a
#     assert d.Connection is None
#     assert d.ExportFolderPath == "/path/to/export"

#     # Test case for invalid input with both connection and export folder path
#     conn = DicomSCP(Title="TestTitle", _allowed_titles=["TestTitle"])
#     a = AnonymizationSettings()
#     with pytest.raises(ValueError, match="Either"):
#         d = DCMExportDestination(
#             name="TestName",
#             AnonymizationSettings=a,
#             Connection=conn,
#             ExportFolderPath="/path/to/export",
#         )

#     # Test case for invalid input with neither connection nor export folder path
#     a = AnonymizationSettings()
#     with pytest.raises(ValueError, match="Either"):
#         d = DCMExportDestination(name="TestName", AnonymizationSettings=a)
