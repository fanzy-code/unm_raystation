"""
    processing_export script to send various DICOM data to multiple locations

    Features:

    Pre-configured DICOM or ExportFolder Destinations with default options for active CT, RTSS, RTPlan, BeamSet Dose/BeamSet BeamDose, DRRs
    Dynamic ExportFolder names, for machine specific folders
    GUI with toggle-able options for changing what needs to be sent
    User feedback for status of exports: Completed, Skipped, or Error
    Full report log for end result

    TODO:


"""
__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "1.0.0"
__license__ = "MIT"

import html
import json
import logging
import queue
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import System  # type: ignore
from connect import *  # type: ignore
from rs_utils import get_current_helper, raise_error, save_patient
from System.Windows import *  # type: ignore
from System.Windows.Controls import *  # type: ignore


@dataclass
class DicomSCP:
    # Needs either Title or Node+Port+CalledAE+CallingAE
    Title: Optional[str] = None

    Node: Optional[str] = None
    Port: Optional[str] = None
    CalledAE: Optional[str] = None
    CallingAE: Optional[str] = None
    _allowed_titles: List[str] = field(default_factory=list)

    def __str__(self):
        return str(self.Title)

    def get_dicomscp_dict(self) -> dict:
        excluded_attrs = ["_allowed_titles"]
        return {k: v for k, v in vars(self).items() if v is not None and k not in excluded_attrs}

    def __post_init__(self):
        if not self.Title and not all((self.Node, self.Port, self.CalledAE, self.CallingAE)):
            raise ValueError(
                "Either Title or all of (Node, Port, CalledAE, CallingAE) have to be defined."
            )

        if self.Title and any((self.Node, self.Port, self.CalledAE, self.CallingAE)):
            raise ValueError(
                "Both Title and (Node, Port, CalledAE, CallingAE) are defined, only one can be."
            )

        if self.Title:
            # Query for allowed titles in ClinicDB
            if not (self._allowed_titles):
                try:
                    _clinic_db = get_current_helper("ClinicDB")
                    self._allowed_titles = [
                        AE.Title
                        for AE in _clinic_db.GetSiteSettings().DicomSettings.DicomApplicationEntities
                    ]
                except:
                    logging.warning("Unable to get titles from clinic_db")

            if not (self.Title in self._allowed_titles):
                raise ValueError(
                    f"Title {self.Title} does not exist in the clinical DB.  Existing ones are {self._allowed_titles}."
                )

        return


@dataclass
class AnonymizationSettings:
    Anonymize: bool = False
    AnonymizedName: str = "anonymizedName"
    AnonymizedID: str = "anonymizedID"
    RetainDates: bool = False
    RetainDeviceIdentity: bool = False
    RetainInstitutionIdentity: bool = False
    RetainUIDS: bool = False
    RetainSafePrivateAttributes: bool = False

    def get_anonymization_settings_dict(self) -> dict:
        return vars(self)


@dataclass
class DCMExportDestination:
    name: str
    AnonymizationSettings: AnonymizationSettings = AnonymizationSettings()

    # Supported
    Active_CT: bool = False
    _Examinations: Optional[List[str]] = None  # Example [examination.Name]

    # Supported
    RtStructureSet_from_Active_CT: bool = False
    _RtStructureSetsForExaminations: Optional[List[str]] = None  # Example [examination.Name]

    # Not supported
    _RtStructureSetsReferencedFromBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    Active_RTPlan: bool = False
    _BeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported
    _RtRadiationSetForBeamSets: Optional[
        List[str]
    ] = None  # CK only: Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported
    _RtRadiationsForBeamSets: Optional[
        List[str]
    ] = None  # CK only: Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    Active_BeamSet_Dose: bool = False
    _PhysicalBeamSetDoseForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not Supported; dose calculated with tissue hetereogeneity
    _EffectiveBeamSetDoseForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    Active_BeamSet_BeamDose: bool = False
    _PhysicalBeamDosesForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not Supported; beam doses calculated with tissue hetereogeneity
    _EffectiveBeamDosesForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported
    _SpatialRegistrationForExaminations: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(fromExamination.Name, toExamination.Name)]

    # Not supported
    _DeformableSpatialRegistrationsForExaminations: Optional[
        List[str]
    ] = None  # Example ["%s:%s:%s"%(case.PatientModel.StructureRegistrationGroups[0].Name, fromExamination.Name, toExamination.Name)]

    # Supported
    TxBeam_DRRs: bool = False
    _TreatmentBeamDrrImages: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported
    SetupBeam_DRRs: bool = False
    _SetupBeamDrrImages: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Not supported, Custom DICOM .filter settings defined in Clinic Settings
    _DicomFilter: str = ""

    _IgnorePreConditionWarnings: bool = False

    # Supported, Choose one but not both
    Connection: Optional[DicomSCP] = None
    ExportFolderPath: Optional[str] = None

    def __post_init__(self):
        if not ((self.Connection is None) ^ (self.ExportFolderPath is None)):
            raise ValueError(
                "Either Connection or ExportFolderPath has to be defined, but not both"
            )
        return

    def update_with_kwargs(self, **kwargs):
        # Update ExportFolderPath
        if self.ExportFolderPath:
            self.ExportFolderPath = self.ExportFolderPath.format(**kwargs)
        return self

    def generate_xaml_attribute_dict(self):
        """
        Generates dictionary with key = class attribute name and dictionary of xaml related values

        Returns:
            _type_: _description_
        """

        xaml_dict = {
            "name": {
                "xaml_display": "Name",
                "xaml_name": f"{self.name}_name",
                "xaml_value": self.name,
            },
            "Connection": {
                "xaml_display": "DICOM Destination",
                "xaml_name": f"{self.name}_Connection",
                "xaml_value": self.Connection,
            },
            "ExportFolderPath": {
                "xaml_display": "Export Folder Path",
                "xaml_name": f"{self.name}_ExportFolderPath",
                "xaml_value": self.ExportFolderPath,
            },
            "Active_CT": {
                "xaml_display": "Active CT",
                "xaml_name": f"{self.name}_Active_CT",
                "xaml_value": self.Active_CT,
            },
            "RtStructureSet_from_Active_CT": {
                "xaml_display": "RT Structure Set",
                "xaml_name": f"{self.name}_RtStructureSet_from_Active_CT",
                "xaml_value": self.RtStructureSet_from_Active_CT,
            },
            "Active_RTPlan": {
                "xaml_display": "RT Plan",
                "xaml_name": f"{self.name}_Active_RTPlan",
                "xaml_value": self.Active_RTPlan,
            },
            "Active_BeamSet_Dose": {
                "xaml_display": "BeamSet Dose",
                "xaml_name": f"{self.name}_Active_BeamSet_Dose",
                "xaml_value": self.Active_BeamSet_Dose,
            },
            "Active_BeamSet_BeamDose": {
                "xaml_display": "Beam Dose",
                "xaml_name": f"{self.name}_Active_BeamSet_BeamDose",
                "xaml_value": self.Active_BeamSet_BeamDose,
            },
            "TxBeam_DRRs": {
                "xaml_display": "Tx Beam DRRs",
                "xaml_name": f"{self.name}_TxBeam_DRRs",
                "xaml_value": self.TxBeam_DRRs,
            },
            "SetupBeam_DRRs": {
                "xaml_display": "Setup Beam DRRs",
                "xaml_name": f"{self.name}_SetupBeam_DRRs",
                "xaml_value": self.SetupBeam_DRRs,
            },
        }

        return OrderedDict(xaml_dict)

    def get_export_kwargs(self):
        # Prepares the export kwargs dictionary for ScriptableDicomExport function

        # Initialize with all variables leading with '_'
        export_kwargs = {
            var_name.lstrip("_"): var_value
            for var_name, var_value in vars(self).items()
            if (var_name.startswith("_") and var_value)
        }

        # Pick a connection type
        if self.Connection and self.ExportFolderPath:
            raise ValueError("Both Connection and ExportFolderPath cannot be defined.")

        if self.Connection:
            export_kwargs["Connection"] = self.Connection.get_dicomscp_dict()
        elif self.ExportFolderPath:
            export_kwargs["ExportFolderPath"] = self.ExportFolderPath
        else:
            raise ValueError("Either Connection or ExportFolderPath must be defined.")

        export_kwargs[
            "AnonymizationSettings"
        ] = self.AnonymizationSettings.get_anonymization_settings_dict()

        return export_kwargs

    def set_export_arguments(
        self, examination: PyScriptObject, beam_set: PyScriptObject  # type: ignore
    ):
        if examination is None:
            raise ValueError("No examination provided")
        if beam_set is None:
            raise ValueError("No beam set provided")

        # Hashmap for class attribute variables to export arguments needed for export
        settings_to_export_arguments = {
            "Active_CT": {"_Examinations": [examination.Name]},
            "RtStructureSet_from_Active_CT": {
                "_RtStructureSetsForExaminations": [examination.Name]
            },
            "Active_RTPlan": {"_BeamSets": [beam_set.BeamSetIdentifier()]},
            "Active_BeamSet_Dose": {
                "_PhysicalBeamSetDoseForBeamSets": [beam_set.BeamSetIdentifier()]
            },
            "Active_BeamSet_BeamDose": {
                "_PhysicalBeamDosesForBeamSets": [beam_set.BeamSetIdentifier()]
            },
            "TxBeam_DRRs": {"_TreatmentBeamDrrImages": [beam_set.BeamSetIdentifier()]},
            "SetupBeam_DRRs": {"_SetupBeamDrrImages": [beam_set.BeamSetIdentifier()]},
        }

        attr_was_set = []
        for attr, props in settings_to_export_arguments.items():
            if getattr(self, attr):
                attr_was_set.append(attr)
                for prop, value in props.items():
                    setattr(self, prop, value)

        return attr_was_set

    def handle_result(self, result):
        try:
            json_string = json.loads(str(result))
            comment_block: str = json_string["Comment"]
            warnings: list[str] = json_string["Warnings"]
            notifications: list[str] = json_string["Notifications"]

            warnings_block = "\n".join(warnings)
            notifications_block = "\n".join(notifications)

            result = f"Comment:\n{comment_block}\n\nWarnings:\n{warnings_block}\n\nNotifications:\n{notifications_block}"

        except ValueError as error:
            logging.info(result)
            # raise_error(f"Error reading completion message.", error)

        return result

    def generate_gui_message(self, success: bool, result=None):
        log_message = ""
        if success:
            status_message = "COMPLETE"
            log_message = f"{self.name} export... COMPLETE\n\n"
        else:
            status_message = "Error"
            log_message = f"{self.name} export... Error\n\n"

        if result:
            log_message += self.handle_result(result)

        # Add some new lines for next set of log messages
        log_message += "\n\n\n"
        return status_message, log_message

    def handle_log_warnings(self, error):
        logging.info(
            f"Error exporting, changing to IgnorePreConditionWarnings = True.  Raw error variable string: {error}"
        )
        return

    def export(self, case: PyScriptObject, examination: PyScriptObject, beam_set: PyScriptObject):  # type: ignore
        attr_was_set = self.set_export_arguments(examination, beam_set)
        if not attr_was_set:
            status_message = "SKIPPED"
            log_message = f"{self.name} export... SKIPPED\n\n"
            print(log_message)
            return status_message, log_message

        export_kwargs = self.get_export_kwargs()

        try:
            print(f"Attempting export for {self.name}")
            result = case.ScriptableDicomExport(**export_kwargs)
            status_message, log_message = self.generate_gui_message(success=True, result=result)
        except System.InvalidOperationException as error:
            print(f"Attempting export for {self.name}, ignoring warnings")
            self.handle_log_warnings(error)
            export_kwargs["IgnorePreConditionWarnings"] = True
            result = case.ScriptableDicomExport(**export_kwargs)
            status_message, log_message = self.generate_gui_message(success=True, result=result)
        except Exception as error:
            print(error)
            status_message, log_message = self.generate_gui_message(
                success=False, result=str(error)
            )
            logging.info(f"Export incomplete, {error}")

        return status_message, log_message


# Define Dicom Destinations in this list
# dcm_destinations = [
#     DCMExportDestination(
#         name="MOSAIQ",
#         Connection=DicomSCP(Title="MOSAIQ"),
#         Active_CT=True,
#         RtStructureSet_from_Active_CT=True,
#         Active_RTPlan=True,
#         TxBeam_DRRs=True,
#         SetupBeam_DRRs=True,
#     ),
#     DCMExportDestination(
#         name="SunCheck",
#         Connection=DicomSCP(Title="SunCheck"),
#         Active_CT=True,
#         RtStructureSet_from_Active_CT=True,
#         Active_RTPlan=True,
#         Active_BeamSet_Dose=True,
#         Active_BeamSet_BeamDose=True,
#     ),
#     DCMExportDestination(
#         name="Velocity",
#         Connection=DicomSCP(Title="Velocity"),
#         Active_CT=True,
#         RtStructureSet_from_Active_CT=True,
#         Active_RTPlan=True,
#         Active_BeamSet_Dose=True,
#     ),
#     DCMExportDestination(
#         name="CRAD",
#         ExportFolderPath="//hsc-cc-crad/CRAD_Patients/{machine_name}",
#         Active_CT=True,
#         RtStructureSet_from_Active_CT=True,
#         Active_RTPlan=True,
#     ),
# ]


# Testing list
dcm_destinations = [
    DCMExportDestination(
        name="MOSAIQ",
        Connection=DicomSCP(Title="MOSAIQ"),
        Active_CT=False,
        RtStructureSet_from_Active_CT=False,
        Active_RTPlan=False,
        TxBeam_DRRs=False,
        SetupBeam_DRRs=False,
    ),
    DCMExportDestination(
        name="SunCheck",
        Connection=DicomSCP(Title="SunCheck"),
        Active_CT=False,
        RtStructureSet_from_Active_CT=False,
        Active_RTPlan=False,
        Active_BeamSet_Dose=False,
        Active_BeamSet_BeamDose=False,
    ),
    DCMExportDestination(
        name="Velocity",
        Connection=DicomSCP(Title="Velocity"),
        Active_CT=False,
        RtStructureSet_from_Active_CT=False,
        Active_RTPlan=False,
        Active_BeamSet_Dose=False,
    ),
    DCMExportDestination(
        name="CRAD",
        ExportFolderPath="//hsc-cc-crad/CRAD_Patients/{machine_name}",
        Active_CT=False,
        RtStructureSet_from_Active_CT=True,
        Active_RTPlan=True,
    ),
]


class MyWindow(RayWindow):  # type: ignore
    def __init__(self, dcm_destinations):
        self.patient: PyScriptObject = get_current_helper("Patient")  # type: ignore
        self.case: PyScriptObject = get_current_helper("Case")  # type: ignore
        self.examination: PyScriptObject = get_current_helper("Examination")  # type: ignore
        self.beam_set: PyScriptObject = get_current_helper("BeamSet")  # type: ignore
        self.kwargs: dict = {"machine_name": self.beam_set.MachineReference.MachineName}

        # Check for saving
        save_patient(self.patient)

        if not dcm_destinations:
            raise_error("No Dicom Destinations set.")

        self.dcm_destinations: list[DCMExportDestination] = [
            dcm_destination.update_with_kwargs(**self.kwargs)
            for dcm_destination in dcm_destinations
        ]

        # Error check for dcm_destinations of same name
        names_seen = set()
        for dcm_destination in self.dcm_destinations:
            if dcm_destination.name in names_seen:
                raise ValueError(f"Duplicate name found: {dcm_destination.name}")
            names_seen.add(dcm_destination.name)

        # Get display headers, cannot fail because dcm_destinations cannot be None
        self.display_table_headers = [
            value_dict["xaml_display"]
            for key, value_dict in self.dcm_destinations[0].generate_xaml_attribute_dict().items()
        ]
        self.display_number_rows = len(dcm_destinations)

        # Initialize the XAML
        xaml = """
        <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" 
        Title="Export Destinations" Height="600" Width="1400">
        <Grid>
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto" />
                <RowDefinition Height="Auto" />
                <RowDefinition Height="225" />
                <RowDefinition Height="Auto" />
            </Grid.RowDefinitions>
            {xaml_table_description}
            {xaml_table}
            <Grid Grid.Row="2" Margin="15,15,15,15">
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*"/>
                </Grid.ColumnDefinitions>
                 <TextBox Name="log_message" Grid.Column="0" HorizontalAlignment="Stretch" VerticalAlignment="Stretch" Margin="10" TextWrapping="Wrap" Text="" ScrollViewer.VerticalScrollBarVisibility="Auto" Width="Auto" Height="Auto"/>
            </Grid>
            <Grid Grid.Row="3" Margin="15,15,15,15">
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*"/>
                </Grid.ColumnDefinitions>
                <Button Width="50" Height="25" Name="cancel" Click="CancelClicked" Content="Close" Grid.Column="0" HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Grid>
        </Grid>
        </Window>
        """

        # Make some modifications to XAML

        # Get the xaml_table by using self properties
        xaml_table_description = self.initialize_xaml_table_description()

        xaml_table = self.initialize_xaml_table()

        # Modify the xaml code
        modified_xaml = xaml.format(
            xaml_table_description=xaml_table_description, xaml_table=xaml_table
        )
        # print(modified_xaml)
        # Load the modified xaml code
        self.LoadComponent(modified_xaml)

        # Set window as topmost window.
        self.Topmost = True

        # Start up window at the center of the screen. WindowStartUpLocation comes from RayStation System Package
        self.WindowStartupLocation = WindowStartupLocation.CenterScreen  # type: ignore

    def initialize_xaml_table_description(self):
        case_name = html.escape(self.case.CaseName)
        exam_name = html.escape(self.examination.Name)
        beam_set_name = html.escape(self.beam_set.BeamSetIdentifier())

        xaml_table_description = """
        <Grid Grid.Row="0" Margin="15,15,15,15">        
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="125"/>
                <ColumnDefinition Width="125"/>
            </Grid.ColumnDefinitions>
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto" />
                <RowDefinition Height="Auto" />
                <RowDefinition Height="Auto" />
            </Grid.RowDefinitions>
                <TextBlock FontSize="12" FontWeight="Bold" Grid.Row="0" Grid.Column="0" Text="Active Case" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" FontWeight="Bold" Grid.Row="1" Grid.Column="0" Text="Active CT" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" FontWeight="Bold" Grid.Row="2" Grid.Column="0" Text="Active Beam Set" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" Grid.Row="0" Grid.Column="1" Text="{case_name}" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" Grid.Row="1" Grid.Column="1" Text="{exam_name}" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" Grid.Row="2" Grid.Column="1" Text="{beam_set_name}" TextWrapping="Wrap"/>
        </Grid>
        """.format(
            case_name=case_name,
            exam_name=exam_name,
            beam_set_name=beam_set_name,
        )
        return xaml_table_description

    def get_xaml_table_row_data(self):
        xaml_dcm_destinations = [
            dcm_destination.generate_xaml_attribute_dict()
            for dcm_destination in self.dcm_destinations
        ]
        xaml_table_rows = """"""
        for row_count, xaml_dcm_destination in enumerate(
            xaml_dcm_destinations, start=1
        ):  # row_count = 0 is for table headers
            for column_count, (class_variable_key, xaml_property_dict) in enumerate(
                xaml_dcm_destination.items()
            ):
                xaml_name = xaml_property_dict["xaml_name"]
                xaml_value = xaml_property_dict["xaml_value"]
                if column_count == 0:
                    xaml_status_name = xaml_name.replace("name", "status")
                if isinstance(xaml_value, (str, DicomSCP)):
                    xaml_table_rows += """<TextBlock Name="{xaml_name}" FontSize="12" Grid.Row="{row_count}" Grid.Column="{column_count}" Text="{value}" TextWrapping="Wrap" Padding="3"/>\n""".format(
                        row_count=row_count,
                        column_count=column_count,
                        xaml_name=xaml_name,
                        value=xaml_value,
                    )
                elif isinstance(xaml_value, bool):
                    xaml_table_rows += """<CheckBox Name="{xaml_name}" IsChecked="{xaml_value}" VerticalAlignment="Center" HorizontalAlignment="Center" Grid.Row="{row_count}" Grid.Column="{column_count}" FontSize="14" Padding="3"/>\n""".format(
                        row_count=row_count,
                        column_count=column_count,
                        xaml_name=xaml_name,
                        xaml_value=xaml_value,
                    )
                elif xaml_value is None:
                    xaml_table_rows += """"""
            # Add a final column for export status
            xaml_table_rows += """<TextBlock Name="{xaml_name}" FontSize="12" Grid.Row="{row_count}" Grid.Column="{column_count}" Text="" TextWrapping="Wrap" HorizontalAlignment="Center" VerticalAlignment="Center" Padding="3"/>\n""".format(
                xaml_name=xaml_status_name,
                row_count=row_count,
                column_count=column_count + 1,
            )
        return xaml_table_rows

    def initialize_xaml_table(self):
        table_headers = self.display_table_headers
        number_of_rows = self.display_number_rows

        # Defines the starting point of XAML table
        xaml_table = """
        <Grid Grid.Row="1" Margin="15,15,15,15">        
            <Grid.ColumnDefinitions>
                {xaml_column_definitions}
            </Grid.ColumnDefinitions>
            <Grid.RowDefinitions>
                {xaml_row_definitions}
            </Grid.RowDefinitions>
                {xaml_table_headers}
                {xaml_table_rows}
        </Grid>
        """

        #  xaml_column_definitions
        number_of_columns = len(table_headers)
        xaml_column_definitions = """"""
        for column_number in range(number_of_columns + 1):
            xaml_column_definitions += """<ColumnDefinition />\n"""

        # xaml_row_definitions
        xaml_row_definitions = """"""
        for row_number in range(number_of_rows + 1):
            xaml_row_definitions += """<RowDefinition />\n"""

        # xaml_table_headers
        xaml_table_headers = """"""
        for column_number, header in enumerate(table_headers):
            xaml_table_headers += """<TextBlock FontSize="12" FontWeight="Bold" Grid.Row="0" VerticalAlignment="Center" HorizontalAlignment="Center" Padding="5" Grid.Column="{column_number}" Text="{header}" TextWrapping="Wrap"/>\n""".format(
                column_number=column_number, header=header
            )
        # Adding a submit button at the end
        xaml_table_headers += """<Button Width="55" Height="25" Name="submit" Click="SubmitClicked" Content="Export" HorizontalAlignment="Center" Grid.Column="{column_number}" VerticalAlignment="Center" IsEnabled="True"/>\n""".format(
            column_number=column_number + 1
        )

        # xaml_table_rows
        xaml_table_rows = self.get_xaml_table_row_data()

        xaml_table = xaml_table.format(
            xaml_column_definitions=xaml_column_definitions,
            xaml_row_definitions=xaml_row_definitions,
            xaml_table_headers=xaml_table_headers,
            xaml_table_rows=xaml_table_rows,
        )

        return xaml_table

    def get_and_set_updated_attributes_from_xaml(self):
        current_xaml_dcm_destinations = [
            dcm_destination.generate_xaml_attribute_dict()
            for dcm_destination in self.dcm_destinations
        ]

        for index, xaml_dcm_destination in enumerate(current_xaml_dcm_destinations):
            for class_variable_key, xaml_property_dict in xaml_dcm_destination.items():
                xaml_name = xaml_property_dict["xaml_name"]
                xaml_property = getattr(self, xaml_property_dict["xaml_name"], None)
                if isinstance(xaml_property, System.Windows.Controls.CheckBox):
                    setattr(
                        self.dcm_destinations[index],
                        class_variable_key,
                        xaml_property.IsChecked,
                    )

    def CancelClicked(self, sender, event):
        # Close window.
        self.DialogResult = False

    def _submit_threading(self):
        tasks = {}
        results_queue = queue.Queue()

        # for loop through the dcm_destinations and run the export function using threading.Thread
        for dcm_destination in self.dcm_destinations:
            task = threading.Thread(
                target=self._export_thread,
                args=(dcm_destination, self.case, self.examination, self.beam_set, results_queue),
            )
            tasks[task] = dcm_destination
            status_attribute_name = dcm_destination.name + "_status"
            status_attribute = getattr(self, status_attribute_name)
            status_attribute.Text = "Exporting..."
            task.start()

        # Update the GUI periodically while the tasks are running
        while tasks:
            try:
                result = results_queue.get_nowait()
                task, status_message, log_message = result
                dcm_destination = tasks[task]
                status_attribute_name = dcm_destination.name + "_status"
                status_attribute = getattr(self, status_attribute_name)
                status_attribute.Text = status_message
                self.log_message.Text += log_message
                del tasks[task]
            except queue.Empty:
                pass
            time.sleep(0.1)

    def _export_thread(self, dcm_destination, case, examination, beam_set, results_queue):
        try:
            status_message, log_message = dcm_destination.export(case, examination, beam_set)
            results_queue.put((threading.current_thread(), status_message, log_message))
        except Exception as error:
            status_message, log_message = self.generate_gui_message(success=False)
            log_message += error
            results_queue.put((threading.current_thread(), status_message, log_message))

    def SubmitClicked(self, sender, event):
        # class InfoWindow(RayWindow):  # type: ignore
        #     def __init__(self):
        #         xaml = """
        #                 <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        #                 Title="Test" Height="600" Width="1400">
        #                 <Grid>
        #                 </Grid>
        #                 </Window>
        #                 """
        #         self.LoadComponent(xaml)

        # info_window = InfoWindow()
        # info_window.ShowDialog()

        try:
            self.get_and_set_updated_attributes_from_xaml()
        except Exception as error:
            logging.exception(error)
            error_message = f"Invalid input."
            raise_error(ErrorMessage=error_message, rs_exception_error=error)

        self.submit.IsEnabled = False
        self._submit_threading()


def main():
    window = MyWindow(dcm_destinations)
    window.ShowDialog()


if __name__ == "__main__":
    main()
