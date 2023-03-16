"""
    processing_export script to send various DICOM data to multiple locations

    Features:

    Pre-configured DICOM or ExportFolder Destinations with default options for active CT, RTSS, RTPlan, BeamSet Dose/BeamSet BeamDose, DRRs
    Dynamic ExportFolder names, for machine specific folders
    GUI with toggle-able options for changing what needs to be sent
    User feedback for status of exports: Completed or Error
    Full report log for end result

    TODO:
    Active_BeamSet_Dose rename to Active_BeamSet_Dose, xaml display name to be BeamSet Dose
    Active_BeamSet_BeamDose rename to Active_Beam_Dose, xaml display name to be Beam Dose


"""
__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "0.1.1"
__license__ = "MIT"

import html
import logging

import System  # type: ignore
from connect import *  # type: ignore
from rs_utils import (
    DCMExportDestination,
    DicomSCP,
    get_current_helper,
    raise_error,
    save_patient,
)

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
        Active_BeamSet_Dose=True,
        Active_BeamSet_BeamDose=True,
    ),
    DCMExportDestination(
        name="Velocity",
        Connection=DicomSCP(Title="Velocity"),
        Active_CT=True,
        RtStructureSet_from_Active_CT=True,
        Active_RTPlan=True,
        Active_BeamSet_Dose=True,
    ),
    DCMExportDestination(
        name="CRAD",
        ExportFolderPath="//hsc-cc-crad/CRAD_Patients/{machine_name}",
        Active_CT=True,
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
        print(modified_xaml)
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

    def SubmitClicked(self, sender, event):
        try:
            self.get_and_set_updated_attributes_from_xaml()
        except Exception as error:
            logging.exception(error)
            error_message = f"Invalid input."
            raise_error(ErrorMessage=error_message, ExceptionError=error)

        self.submit.IsEnabled = False
        # for loop through the dcm_destinations and run the export function
        for row_count, dcm_destination in enumerate(self.dcm_destinations):
            status_message, log_message = dcm_destination.export(
                self.case, self.examination, self.beam_set
            )
            status_attribute_name = dcm_destination.name + "_status"
            status_attribute = getattr(self, status_attribute_name)
            status_attribute.Text = status_message
            self.log_message.Text += log_message


def main():
    window = MyWindow(dcm_destinations)
    window.ShowDialog()


if __name__ == "__main__":
    main()
