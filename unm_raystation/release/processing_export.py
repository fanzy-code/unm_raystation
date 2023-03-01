"""
Script to export plans to multiple locations
"""

import json
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional

import System  # type: ignore
from connect import *  # type: ignore
from rs_utils import raise_error  # type: ignore
from rs_utils import get_current_helper
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
                    _clinic_db = get_current("ClinicDB")
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
    anonymize: bool = False
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

    # Not supported; for no tissue hetereogeneity
    _PhysicalBeamSetDoseForBeamSets: Optional[
        List[str]
    ] = None  # Example ["%s:%s"%(plan.Name, beam_set.DicomPlanLabel)] or [beam_set.BeamSetIdentifier()]

    # Supported; dose calculated with tissue hetereogeneity
    RTDose_for_active_BeamSet_with_hetereogeneity_correction: bool = False
    _EffectiveBeamSetDoseForBeamSets: Optional[
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

    def get_display_export_args(self):
        # ordered list of Name, Connection, ExportFolderPath, Active_CT,
        # RtStructureSet_from_Active_CT, Active_RTPlan,
        # RTDose_for_active_BeamSet_with_hetereogeneity_correction, TxBeam_DRRs, SetupBeam_DRRs
        display_dictionary = {
            "Name": self.name,
            "Connection": self.Connection,
            "Export Folder": self.ExportFolderPath,
            "(Active) CT": self.Active_CT,
            "(Active) RT Structure Set": self.RtStructureSet_from_Active_CT,
            "(Active) RT Plan": self.ActiveRTPlan,
            "(Active) RT Dose w/ hetereogeneity corrections": self.RTDose_for_active_BeamSet_with_hetereogeneity_correction,
            "(Active) Treatment Beam DRRs": self.TxBeam_DRRs,
            "(Active) Setup Beam DRRs": self.SetupBeam_DRRs,
        }
        return OrderedDict(display_dictionary)

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
        self, examination: PyScriptObject, beam_set: PyScriptObject, **kwargs  # type: ignore
    ):
        if examination is None:
            raise ValueError("No examination provided")
        if beam_set is None:
            raise ValueError("No beam set provided")

        # Set export arguments for dicom objects needed
        settings_to_export_arguments = {
            "Active_CT": {"_Examinations": [examination.Name]},
            "RtStructureSet_from_Active_CT": {
                "_RtStructureSetsForExaminations": [examination.Name]
            },
            "Active_RTPlan": {"_BeamSets": [beam_set.BeamSetIdentifier()]},
            "RTDose_for_active_BeamSet_with_hetereogeneity_correction": {
                "_EffectiveBeamSetDoseForBeamSets": [beam_set.BeamSetIdentifier()]
            },
            "TxBeam_DRRs": {"_TreatmentBeamDrrImages": [beam_set.BeamSetIdentifier()]},
            "SetupBeam_DRRs": {"_SetupBeamDrrImages": [beam_set.BeamSetIdentifier()]},
        }

        for attr, props in settings_to_export_arguments.items():
            if getattr(self, attr):
                for prop, value in props.items():
                    setattr(self, prop, value)

        # Format ExportFolderPath string
        if self.ExportFolderPath:
            self.ExportFolderPath = self.ExportFolderPath.format(**kwargs)

        return

    # Get rid of these print statements and put it in logging or something
    def handle_log_completion(self, result):
        try:
            jsonWarnings = json.loads(str(result))
            print("Completed!")
            print("Comment:")
            print(jsonWarnings["Comment"])
            print("Warnings:")
            for w in jsonWarnings["Warnings"]:
                print(w)
            print("Export notifications:")
            # Export notifications is a list of notifications that the user should read.
            for w in jsonWarnings["Notifications"]:
                print(w)
        except ValueError as error:
            raise_error(f"Error reading completion message.", error)

    def handle_log_warnings(self, error):
        try:
            jsonWarnings = json.loads(str(error))
            # If the json.loads() works then the script was stopped due to
            # a non-blocking warning.
            print("WARNING! Export Aborted!")
            print("Comment:")
            print(jsonWarnings["Comment"])
            print("Warnings:")

            # Here the user can handle the warnings. Continue on known warnings,
            # stop on unknown warnings.
            for w in jsonWarnings["Warnings"]:
                print(w)
        except ValueError as error:
            raise_error(f"DICOM export unsuccessful.  Error reading warning message.", error)

    def handle_log_errors(self, error):
        raise_error(f"Error exporting DICOM", error)
        return

    def export(self, case: PyScriptObject, examination: PyScriptObject, beam_set: PyScriptObject):  # type: ignore
        self.set_export_arguments(examination, beam_set)
        export_kwargs = self.get_export_kwargs()

        try:
            result = case.ScriptableDicomExport(**export_kwargs)
            self.handle_log_completion(result)
        except System.InvalidOperationException as error:
            self.handle_log_warnings(error)
            export_kwargs["IgnorePreConditionWarnings"] = True
            result = case.ScriptableDicomExport(**export_kwargs)
            self.handle_log_completion(result)
        except Exception as error:
            self.handle_log_errors(error)

        return


dcm_destinations = [
    DCMExportDestination(
        name="MOSAIQ",
        Connection=DicomSCP(Title="MOSAIQ"),
        Active_CT=True,
        RtStructureSet_from_Active_CT=True,
        Active_RTPlan=True,
        TxBeam_DRRs=True,
        SetupBeam_DRRs=True,
    ),
    DCMExportDestination(
        name="SunCheck",
        Connection=DicomSCP(Title="SunCheck"),
        Active_CT=True,
        RtStructureSet_from_Active_CT=True,
        Active_RTPlan=True,
        RTDose_for_active_BeamSet_with_hetereogeneity_correction=True,
    ),
    DCMExportDestination(
        name="Velocity",
        Connection=DicomSCP(Title="Velocity"),
        Active_CT=True,
        RtStructureSet_from_Active_CT=True,
        Active_RTPlan=True,
        RTDose_for_active_BeamSet_with_hetereogeneity_correction=True,
    ),
    DCMExportDestination(
        name="CRAD",
        ExportFolderPath="\hsc-cc-crad\CRAD Patients{machine_name}",
        Active_CT=True,
        RtStructureSet_from_Active_CT=True,
        Active_RTPlan=True,
    ),
]


class MyWindow(RayWindow):  # type: ignore
    xaml = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" 
    Title="MainWindow" Height="450" Width="800">
        {xaml_table}
    </Window>
    """

    def __init__(self, dcm_destinations):
        self.case: PyScriptObject = get_current_helper("Case")
        self.examination: PyScriptObject = get_current_helper("Examination")
        self.beam_set: PyScriptObject = get_current_helper("BeamSet")
        self.kwargs: dict = {"machine_name": self.beam_set.MachineReference.MachineName}

        self.dcm_destinations: list[DCMExportDestination] = dcm_destinations

        # Get display headers, cannot fail because dcm_destinations cannot be None
        self.display_table_headers = self.dcm_destinations[0].get_display_export_args().keys()
        self.display_number_rows = len(dcm_destinations)

        # Make some modifications to XAML

        # Get the xaml_table by using self properties
        xaml_table = self.initialize_xaml_table(
            self.display_table_headers, self.display_number_rows
        )

        # Modify the xaml code
        self.xaml = self.xaml.format(xaml_table)

        # Load the modified xaml code
        self.LoadComponent(self.xaml)

    def initialize_xaml_table(self, table_headers, number_of_rows):
        # Defines the starting point of XAML table
        xaml_table = """
        <Grid>        
            <Grid.ColumnDefinitions>
                {columns_definition_xaml}
            </Grid.ColumnDefinitions>
            <Grid.RowDefinitions>
                {rows_definition_xaml}
            </Grid.RowDefinitions>
                {headers_xaml}
                {rows_xaml}
        </Grid>
        """

        number_of_columns = len(table_headers)
        columns_definition_xaml = """"""
        for column_number in range(number_of_columns):
            columns_definition_xaml += """<ColumnDefinition />"""

        rows_definition_xaml = """"""
        for row_number in range(number_of_rows):
            rows_definition_xaml += """<RowDefinition Height="30" />"""

        headers_xaml = """"""
        for column_number, header in enumerate(table_headers):
            headers_xaml += """<TextBlock FontSize="16" FontWeight="Bold" Grid.Row="0" Grid.Column="{column_number}"    
                   Text="{header}" />""".format(
                column_number=column_number, header=header
            )

        rows_xaml = """"""

        xaml_table.format(
            columns_definition_xaml=columns_definition_xaml,
            rows_definition_xaml=rows_definition_xaml,
            headers_xaml=headers_xaml,
            rows_xaml=rows_xaml,
        )

        return xaml_table


def main():
    window = MyWindow()
    window.ShowDialog()

    # run the GUI to list all the export destinations in a row

    # for loop export ideally


if __name__ == "__main__":
    main()
