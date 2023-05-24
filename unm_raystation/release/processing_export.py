"""
processing_export script to send various DICOM data to multiple locations

Features:
Multiple beam_sets support
Pre-configured DICOM or ExportFolder Destinations with default options for active CT, RTSS, RTPlan, BeamSet Dose/BeamSet BeamDose, DRRs
Dynamic ExportFolder names, for machine specific folders
GUI with toggle-able options for changing what needs to be sent
User feedback for status of exports: Completed, Skipped, or Error
Full report log for end result


TODO:

Asynchronous export and update solution per Cameron:


Create a timer and a thread: 
from System.Windows.Forms import Timer
from threading import Lock, Thread
from queue import Queue

in the method that will start the export:
    self.MyTimer = Timer()
    self.MyTimer.Interval = 20  # 20 millisecond interval (basic event polling)
    self.MyTimer.Tick +=  self.checkstatus  # event for the timer tick

in the same method create the thread for starting the export:
    self.lock = Lock()
    self.queue = Queue()
  self.exportThread = Thread(target=async_Export, args=(self.exportParameters, self.lock, self.Queue))

Use lock and queue to send state and messages. And update the ui in the self.checkstatus method.

Cameron


Regards,

Cameron Ditty, MSc, DABR
Senior Physics Specialist
"""
__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "1.0.0"
__license__ = "MIT"

import html
import logging
import queue
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from util_raystation_general import get_current_helper, raise_error, save_patient
from util_raystation_networking import DCMExportDestination, DicomSCP

import System
from connect import *
from System.Windows import *  # type: ignore
from System.Windows.Controls import *  # type: ignore

# Define Dicom Destinations in this list
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


class ProcessingExportGUI(RayWindow):
    def __init__(self, dcm_destinations):
        self.patient: PyScriptObject = get_current_helper("Patient")
        self.case: PyScriptObject = get_current_helper("Case")
        self.examination: PyScriptObject = get_current_helper("Examination")
        self.plan: PyScriptObject = get_current_helper("Plan")
        self.beam_sets: List[PyScriptObject] = self.plan.BeamSets  # type: ignore
        self.active_beam_set: PyScriptObject = get_current_helper("BeamSet")
        self.dcm_destinations: list[DCMExportDestination] = dcm_destinations

        # Error check for no dcm_destinations
        if not dcm_destinations:
            raise_error(
                "No Dicom Destinations set.", rs_exception_error=AttributeError, terminate=True
            )

        # Error check for dcm_destinations of same name
        names_seen = set()
        for dcm_destination in self.dcm_destinations:
            if dcm_destination.name in names_seen:
                error_message = f"Duplicate DICOM destination found: {dcm_destination.name}"
                raise_error(error_message, rs_exception_error=ValueError, terminate=True)
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

        ### Make some modifications to XAML

        # Get the xaml_table by using self properties
        xaml_table_description = self.initialize_xaml_table_description()

        xaml_table = self.initialize_xaml_table()

        # Modify the xaml code
        modified_xaml = xaml.format(
            xaml_table_description=xaml_table_description, xaml_table=xaml_table
        )

        # Optional: print the modified xaml code for debugging
        # print(modified_xaml)

        # Load the modified xaml code
        self.LoadComponent(modified_xaml)

        # Set window as topmost window.
        self.Topmost = False

        # Start up window at the center of the screen. WindowStartUpLocation comes from RayStation System Package
        self.WindowStartupLocation = WindowStartupLocation.CenterScreen  # type: ignore

    def initialize_xaml_table_description(self):
        case_name = html.escape(self.case.CaseName)  # type: ignore
        exam_name = html.escape(self.examination.Name)  # type: ignore
        plan_name = html.escape(self.plan.Name)  # type: ignore

        xaml_beam_sets = self.initialize_xaml_beam_sets()

        xaml_table_description = """
        <Grid Grid.Row="0" Margin="15,15,15,15">        
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="125"/>
                <ColumnDefinition Width="Auto"/>
            </Grid.ColumnDefinitions>
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto" />
                <RowDefinition Height="Auto" />
                <RowDefinition Height="Auto" />
                <RowDefinition Height="Auto" />
            </Grid.RowDefinitions>
                <TextBlock FontSize="12" FontWeight="Bold" Grid.Row="0" Grid.Column="0" Text="Active Case" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" FontWeight="Bold" Grid.Row="1" Grid.Column="0" Text="Active CT" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" FontWeight="Bold" Grid.Row="2" Grid.Column="0" Text="Active Plan" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" FontWeight="Bold" Grid.Row="3" Grid.Column="0" Text="Beam Sets" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" Grid.Row="0" Grid.Column="1" Text="{case_name}" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" Grid.Row="1" Grid.Column="1" Text="{exam_name}" TextWrapping="Wrap"/>
                <TextBlock FontSize="12" Grid.Row="2" Grid.Column="1" Text="{plan_name}" TextWrapping="Wrap"/>
                {xaml_beam_sets}
        </Grid>
        """.format(
            case_name=case_name,
            exam_name=exam_name,
            plan_name=plan_name,
            xaml_beam_sets=xaml_beam_sets,
        )
        return xaml_table_description

    def initialize_xaml_beam_sets(self):
        beam_sets_name = [html.escape(beam_set.DicomPlanLabel) for beam_set in self.beam_sets]  # type: ignore
        column_definition = """"""
        column_data = """"""
        for column_count, beam_set_name in enumerate(beam_sets_name):
            if beam_set_name == self.active_beam_set.DicomPlanLabel:
                xaml_bold = """FontWeight=\"Bold\""""
                check = True
            else:
                xaml_bold = """"""
                check = False
            column_definition += (
                """<ColumnDefinition Width="20"/>\n<ColumnDefinition Width="Auto"/>\n"""
            )

            column_data += """<CheckBox Name="beam_set_{column_count}" IsChecked="{check}" VerticalAlignment="Center" HorizontalAlignment="Center" Grid.Column="{column_count_checkbox}" Grid.Row="0" FontSize="12" Padding="3"/> <TextBlock Grid.Column="{column_count_textblock}" Grid.Row="0" Text="{beam_set_name}" {xaml_bold} Padding="0,0,20,0"/>\n""".format(
                column_count_checkbox=column_count * 2,
                beam_set_name=beam_set_name,
                check=check,
                column_count_textblock=column_count * 2 + 1,
                column_count=column_count,
                xaml_bold=xaml_bold,
            )

        # Grid row 3 and column 1 brings it to correct table position
        xaml_beam_sets = """
        <Grid Grid.Row="3" Grid.Column="1" Margin="5">
            <Grid.ColumnDefinitions>
                {column_definition}
            </Grid.ColumnDefinitions>
                {column_data}
        </Grid>
        """.format(
            column_definition=column_definition, column_data=column_data
        )

        return xaml_beam_sets

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
        column_number = 0
        for column_number, header in enumerate(table_headers):
            xaml_table_headers += """<TextBlock FontSize="12" FontWeight="Bold" Grid.Row="0" VerticalAlignment="Center" HorizontalAlignment="Center" Padding="5" Grid.Column="{column_number}" Text="{header}" TextWrapping="Wrap"/>\n""".format(
                column_number=column_number, header=header
            )
        # Adding a submit button at the end
        xaml_table_headers += """<Button Width="55" Height="25" Name="submit" Click="SubmitClicked" Content="Export" HorizontalAlignment="Center" Grid.Column="{column_number}" VerticalAlignment="Center" IsEnabled="True"/>\n""".format(
            column_number=column_number + 1
        )

        # initialize xaml_table_rows data
        xaml_table_rows = self.get_xaml_table_row_data()

        xaml_table = xaml_table.format(
            xaml_column_definitions=xaml_column_definitions,
            xaml_row_definitions=xaml_row_definitions,
            xaml_table_headers=xaml_table_headers,
            xaml_table_rows=xaml_table_rows,
        )

        return xaml_table

    def get_xaml_table_row_data(self):
        xaml_dcm_destinations = [
            dcm_destination.generate_xaml_attribute_dict()
            for dcm_destination in self.dcm_destinations
        ]
        xaml_table_rows = """"""
        for row_count, xaml_dcm_destination in enumerate(
            xaml_dcm_destinations, start=1
        ):  # row_count = 0 is for table headers
            column_count = 0
            xaml_status_name = """"""

            # Create check boxes and display names for each column
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

            # Manually add a final column for export status
            xaml_table_rows += """<TextBlock Name="{xaml_name}" FontSize="12" Grid.Row="{row_count}" Grid.Column="{column_count}" Text="" TextWrapping="Wrap" HorizontalAlignment="Center" VerticalAlignment="Center" Padding="3"/>\n""".format(
                xaml_name=xaml_status_name,
                row_count=row_count,
                column_count=column_count + 1,
            )
        return xaml_table_rows

    def get_and_set_updated_attributes_from_xaml(self):
        current_xaml_dcm_destinations = [
            dcm_destination.generate_xaml_attribute_dict()
            for dcm_destination in self.dcm_destinations
        ]

        for index, xaml_dcm_destination in enumerate(current_xaml_dcm_destinations):
            for class_variable_key, xaml_property_dict in xaml_dcm_destination.items():
                xaml_name = xaml_property_dict["xaml_name"]
                xaml_property = getattr(self, xaml_property_dict["xaml_name"], None)
                if isinstance(xaml_property, System.Windows.Controls.CheckBox):  # type: ignore
                    setattr(
                        self.dcm_destinations[index],
                        class_variable_key,
                        xaml_property.IsChecked,  # type: ignore
                    )
        return

    def CancelClicked(self, sender, event):
        # Close window
        self.DialogResult = False

    def get_checked_beam_sets(self) -> List[PyScriptObject]:  # type: ignore
        checked_beam_sets = []
        for index, beam_set in enumerate(self.beam_sets):
            attribute_name = f"beam_set_{index}"
            xaml_attribute = getattr(self, attribute_name)
            if xaml_attribute.IsChecked:
                checked_beam_sets.append(beam_set)

        return checked_beam_sets

    def _submit_threading(self):
        checked_beam_sets = self.get_checked_beam_sets()
        tasks = {}
        results_queue = queue.Queue()

        # Create and start export thread for each dcm_destination
        for dcm_destination in self.dcm_destinations:
            for beam_set in checked_beam_sets:
                updated_dcm_destination = dcm_destination.update_with_beam_set(beam_set)
                task = threading.Thread(
                    target=self._export_thread,
                    args=(
                        updated_dcm_destination,
                        self.case,
                        self.examination,
                        beam_set,
                        results_queue,
                    ),
                )
                tasks[task] = updated_dcm_destination
                status_attribute_name = f"{updated_dcm_destination.name}_status"
                status_attribute = getattr(self, status_attribute_name)
                status_attribute.Text = "Exporting..."
                task.start()

        # Update the GUI periodically while the tasks are running
        while tasks:
            try:
                result = results_queue.get_nowait()
                task, status_message, log_message = result
                updated_dcm_destination = tasks[task]
                status_attribute_name = f"{updated_dcm_destination.name}_status"
                status_attribute = getattr(self, status_attribute_name)
                status_attribute.Text = status_message
                self.log_message.Text += log_message  # type: ignore
                del tasks[task]
            except queue.Empty:
                pass
            time.sleep(0.1)

    def _export_thread(self, dcm_destination, case, examination, beam_set, results_queue):
        try:
            status_message, log_message = dcm_destination.export(case, examination, beam_set)
            results_queue.put((threading.current_thread(), status_message, log_message))
        except Exception as error:
            status_message, log_message = dcm_destination.generate_gui_message(
                beam_set_name=beam_set.Name, success=False
            )
            log_message += str(error)
            results_queue.put((threading.current_thread(), status_message, log_message))

    def _submit_single_thread(self):
        checked_beam_sets = self.get_checked_beam_sets()

        # Create and start export thread for each dcm_destination
        for dcm_destination in self.dcm_destinations:
            for beam_set in checked_beam_sets:
                updated_dcm_destination = dcm_destination.update_with_beam_set(beam_set)
                try:
                    status_message, log_message = updated_dcm_destination.export(
                        self.case, self.examination, beam_set
                    )

                except Exception as error:
                    status_message, log_message = updated_dcm_destination.generate_gui_message(
                        beam_set_name=beam_set.Name, success=False
                    )
                    log_message += str(error)

                status_attribute_name = f"{updated_dcm_destination.name}_status"
                status_attribute = getattr(self, status_attribute_name)
                if status_attribute.Text is not "Error":
                    status_attribute.Text = status_message
                self.log_message.Text += log_message  # type: ignore

    def SubmitClicked(self, sender, event):
        try:
            self.get_and_set_updated_attributes_from_xaml()
            self.submit.IsEnabled = False  # type: ignore
            start_time = time.time()

            self._submit_threading()
            # self._submit_single_thread()

            end_time = time.time()
            elapsed_time = end_time - start_time
            self.log_message.Text += f"Elapsed time: {elapsed_time:.2f} seconds\n"  # type: ignore

        except Exception as error:
            logging.exception(error)
            error_message = f"Invalid input."
            raise_error(error_message=error_message, rs_exception_error=error, terminate=False)


def main_processing_export():
    window = ProcessingExportGUI(dcm_destinations)
    window.ShowDialog()  # type: ignore


if __name__ == "__main__":
    main_processing_export()
