"""
    field_namer script to rename treatment beams and setup beams to UNM naming convention

    Supported beam properties:
        - Arc or Static
        - Bolus
        - Gantry position or source position
        - Couch position
        - BeamSet name
    Renames all field isocenters to BeamSet name
    Last setup field is always named as XVI

    Features:

    Makes best guess for field numbering based on the existing fields in the treatment planning system
    Prompts user with GUI to verify starting number inputs
    Validates user input
    Handles beam name and beam description duplicates


"""

__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "0.1.0"
__license__ = "MIT"

### Code block required only for development in jupyter notebook, omit for production code

# import os
# import sys
# raystation_pid = os.environ['RAYSTATION_PID']
# ScriptClient_path = 'C:\\Program Files\\RaySearch Laboratories\\RayStation 11B-SP2\\ScriptClient'
# sys.path.append(ScriptClient_path)
# environment_scripts_path = os.path.join(os.environ['TEMP'], 'RaySearch\RayStation\Scripts', raystation_pid.split('_')[0], raystation_pid)
# sys.path.append(environment_scripts_path)

###

# Code block for importing RayStation System modules

import logging
import re

import rs_utils  # type: ignore
import System  # type: ignore
from connect import *  # type: ignore
from System.Windows import *  # type: ignore
from System.Windows.Controls import *  # type: ignore

# Main body of code starting here


class PatientWrapper:
    # Wraps the RayStation Patient Class into my own, to provide new methods

    # Initialize with patient and beam_set object
    # Workaround provided by Yibing Wang on Raystation community scripting forums
    def __init__(self, patient, beam_set):
        self._Patient = patient
        self._BeamSet = beam_set

    def get_all_beam_names(self, beam_type):
        # Function to get all beam names of the patient for beam_type = 'Treatment' or 'Setup'
        # Ignores current beam set

        # Get all cases
        cases = [case for case in self._Patient.Cases]

        # Initialize a list
        beam_names = []

        # Nested for loop through all cases, plans, and beam_sets
        for case in cases:
            for plan in case.TreatmentPlans:
                for beam_set in plan.BeamSets:
                    # Exclude current beam_set
                    if beam_set.UniqueId == self._BeamSet.UniqueId:
                        continue

                    # Wrap the current plan and beam set to get wrapper functions
                    beam_set_wrapper = BeamSetWrapper(plan, beam_set)

                    # Append TX beam names
                    if beam_type == "Treatment":
                        beam_names.append(beam_set_wrapper.get_beam_names())

                    # Append patient setup beams
                    if beam_type == "Setup":
                        beam_names.append(beam_set_wrapper.get_setup_beam_names())

        # Flattens the list
        # See https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
        beam_names = [item for sublist in beam_names for item in sublist]

        return beam_names

    def guess_starting_beam_number(self, re_match_string, previous_beam_list):
        # Use regular expression to determine best guess of previous_beam_list

        # Iterate over previous_beam_list and find matches to regular expression string
        match_list = []
        for previous_beam_name in previous_beam_list:
            matched_string = re.search(re_match_string, previous_beam_name)
            if matched_string:
                match_list.append(int(matched_string.group()))

        # Remove duplicate numbers
        match_list = set(match_list)

        # Default guess of 1, otherwise find max number of match list and increment by 1
        guess = 1
        if match_list:
            guess = max(match_list) + 1

        return guess


class BeamSetWrapper:
    # Wraps the RayStation BeamSet Class into my own, to provide new methods
    # Pass an instance of the object to initialize
    # Workaround provided by Yibing Wang on Raystation community scripting forums

    def __init__(self, plan, beam_set):
        self._BeamSet = beam_set
        self._Plan = plan

    def __getattr__(self, name):
        return getattr(self._BeamSet, name)

    def get_treatment_plan_name(self):
        # Returns associated plan name
        return self._Plan.Name

    def ApplyMyNamingConvention(self):
        # Set BeamSet name to Plan Name
        self._BeamSet.DicomPlanLabel = (
            (self._Plan.Name[0:16]) if len(self._Plan.Name) > 16 else self._Plan.Name
        )
        return

    def get_beam_names(self):
        # Returns a list of current beam_names
        return [beam.Name for beam in self._BeamSet.Beams]

    def get_beam_descriptions(self):
        # Returns a list of current beam descriptions
        return [beam.Description for beam in self._BeamSet.Beams]

    def get_setup_beam_names(self):
        # Returns a list of current setup_beam_names
        return [setup_beam.Name for setup_beam in self._BeamSet.PatientSetup.SetupBeams]

    def rename_beam_name_description_duplicates(
        self,
        name_or_description,
        full_set_of_beams,
        new_beam_string,
        full_set_current_beam_strings=[],
        ignore_index=None,
    ):
        # RayStation does not allow duplicate beam names and descriptions in a beam set
        # This function renames offenders with a temporary name

        # If beam strings was not passed as an argument, get an updated current beam names or descriptions
        if not full_set_current_beam_strings:
            if name_or_description == "name":
                full_set_current_beam_strings = self.get_beam_names()
            elif name_or_description == "description":
                full_set_current_beam_strings = self.get_beam_descriptions()

        # if the new beam string is exists in the beam_set already
        if new_beam_string in full_set_current_beam_strings:
            # get the index of the duplicate
            duplicate_beam_index = full_set_current_beam_strings.index(new_beam_string)

            # rename the duplicate beam name or description with an additional "z" if it is not ignored
            if duplicate_beam_index != ignore_index:
                if name_or_description == "name":
                    full_set_of_beams[
                        duplicate_beam_index
                    ].Name += "z"  # Rename duplicate offender to a temporary name
                elif name_or_description == "description":
                    full_set_of_beams[
                        duplicate_beam_index
                    ].Description += "z"  # Rename duplicate offender to a temporary name

        return

    def make_list_unique(self, list_of_names):
        # Adds a suffix for enumeration if list_of_names contain duplicates
        # See https://stackoverflow.com/questions/30650474/python-rename-duplicates-in-list-with-progressive-numbers-without-sorting-list
        new_list = []
        for i, v in enumerate(list_of_names):
            total_count = list_of_names.count(v)
            count = list_of_names[:i].count(v)
            if count == 0:
                new_list.append(v)
            else:
                new_list.append(v + "_" + str(count + 1) if total_count > 1 else v)

        return new_list

    def get_new_beam_names_descriptions(self, beams, starting_beam_number, ignore_beam=[]):
        # Pass beams list (treatment or setup) to create a list of new names and descriptions tuple
        beam_index = []
        new_beam_names = []
        new_beam_descriptions = []
        for beam_number_index, beam in enumerate(beams):
            if beam_number_index in ignore_beam:
                continue

            # Wrap the beam object to include additional class methods
            beam_wrapper = BeamWrapper(plan=self._Plan, beam_set=self._BeamSet, beam=beam)

            # Assign new beam number
            new_beam_number = starting_beam_number + beam_number_index

            # Generate new beam name and beam description
            new_beam_name, new_beam_description = beam_wrapper.GetMyBeamNamingConvention(
                new_beam_number
            )

            # Append to initialized list
            beam_index.append(beam_number_index)
            new_beam_names.append(new_beam_name)
            new_beam_descriptions.append(new_beam_description)

        # New beam names and descriptions cannot have duplicates in them
        new_beam_names = self.make_list_unique(new_beam_names)
        new_beam_descriptions = self.make_list_unique(new_beam_descriptions)

        return list(zip(beam_index, new_beam_names, new_beam_descriptions))

    def rename_my_beams(self, beams, new_beam_names_descriptions, rename_iso=True, ignore_beam=[]):
        # Function to rename passed beams in beam_names_description zip
        # beams must be full set of beams of either treatment or setup type

        # Current beam names
        current_beam_names = [beam.Name for beam in beams]

        # Current beam descriptions
        current_beam_descriptions = [beam.Description for beam in beams]

        # Iterate over the beams
        for beam_number_index, beam in enumerate(beams):
            if beam_number_index in ignore_beam:
                continue

            # Wrap the beam object to include additional class methods
            beam_wrapper = BeamWrapper(plan=self._Plan, beam_set=self._BeamSet, beam=beam)

            # New beam_name and beam_description
            selected_item = [
                (b, c) for a, b, c in new_beam_names_descriptions if a == beam_number_index
            ]

            new_beam_name = selected_item[0][0]
            new_beam_description = selected_item[0][1]

            # Get current beam name and beam_description
            current_beam_name, current_beam_description = beam_wrapper.get_name_description()

            # Pass to function to handle possible duplicate beam names and descriptions in beam set, exclude current beam
            self.rename_beam_name_description_duplicates(
                "name", beams, new_beam_name, current_beam_names, ignore_index=beam_number_index
            )
            self.rename_beam_name_description_duplicates(
                "description",
                beams,
                new_beam_description,
                current_beam_descriptions,
                ignore_index=beam_number_index,
            )

            # Rename the beam
            beam_wrapper.ApplyMyBeamNaming(
                beam_name_string=new_beam_name, beam_description_string=new_beam_description
            )

            # Update the temporary list of beam names and descriptions for handling duplicates
            current_beam_names[beam_number_index] = new_beam_name
            current_beam_descriptions[beam_number_index] = new_beam_description

            if rename_iso:
                # Rename the isocenter to beam_set name
                beam_wrapper.RenameIsocenter(self._BeamSet.DicomPlanLabel)

        return


class BeamWrapper:
    # Wraps the RayStation Beam Class to provide additional methods
    # Pass an instance of the beam object to initialize

    def __init__(self, plan, beam_set, beam):
        self._Plan = plan
        self._BeamSet = beam_set
        self._Beam = beam

    def __getattr__(self, name):
        return getattr(self._Beam, name)

    def get_new_beam_name(self, beam_number):
        # Delivery technique lookup dictionary
        # See RayStation Scripting API: DeliveryTechnique
        delivery_technique_lookup = {
            "DynamicArc": "A",
            "StaticArc": "A",
            "CollapsedArc": "A",
            "Setup": "SU",
        }

        # String format with placeholder
        beam_name_string_format = "{delivery_technique}{beam_number:02d}{bolus}"

        # Determine the beam name prefix based on the beam delivery technique
        delivery_technique = delivery_technique_lookup.get(self._Beam.DeliveryTechnique, "")

        # Check if a list of boli is assigned to beam
        bolus = ""
        if self._Beam.Boli:
            # Bolus exists
            bolus = "B"

        return beam_name_string_format.format(
            delivery_technique=delivery_technique, beam_number=beam_number, bolus=bolus
        )

    def get_gantry_string(self):
        # String formats with placeholder, gantry_angle formatted to truncated 0 decimal integer
        if self._Beam.DeliveryTechnique == "Setup":
            # Source Angle
            gantry_string_format = "S{gantry_angle:.0f}"
        else:
            # Gantry Angle
            gantry_string_format = "G{gantry_angle:.0f}"

        return gantry_string_format.format(gantry_angle=int(self._Beam.GantryAngle))

    def get_couch_string(self, blank_if_zero=True):
        # String format with placeholder, couch_rotation_angle formatted to truncated 0 decimal integer
        couch_string_format = "C{couch_position:.0f}"

        # Convert couch position to integer
        couch_position = int(self._Beam.CouchRotationAngle)

        # Return empty string for couch position if conditions are right
        if not couch_position and blank_if_zero:
            return ""

        # Return empty string for setup fields
        if self._Beam.DeliveryTechnique == "Setup":
            return ""

        return couch_string_format.format(couch_position=couch_position)

    def get_name_description(self):
        # Returns current beam name and description
        return (self._Beam.Name, self._Beam.Description)

    def GetMyBeamNamingConvention(self, beam_number):
        # Returns new beam name and new beam description

        # Beam name string: A01, A02, etc.
        new_beam_name_string = self.get_new_beam_name(beam_number=beam_number)

        # Gantry string: G330, G180, etc.  (G180.1 would be truncated to G180)
        gantry_string = self.get_gantry_string()

        # Couch string: C10, C330, etc.
        couch_string = self.get_couch_string(blank_if_zero=False)

        # Beam Set name string
        beam_set_name = self._BeamSet.DicomPlanLabel

        # Ordering the string list for description
        ordered_string_list = [gantry_string, couch_string, beam_set_name]

        # Join the ordered_string_list to form new beam description
        new_beam_description_string = " ".join([word for word in ordered_string_list if word])

        return (new_beam_name_string, new_beam_description_string)

    def ApplyMyBeamNaming(self, beam_name_string, beam_description_string):
        if not self._Beam.Name == beam_name_string:
            try:
                self._Beam.Name = beam_name_string
            except System.InvalidOperationException as error:
                logging.exception(error)
                error_message = f"Cannot set beam name {self._Beam.Name} to {beam_name_string}."
                rs_utils.raise_error(ErrorMessage=error_message, ExceptionError=error)

        if not self._Beam.Description == beam_description_string:
            try:
                self._Beam.Description = beam_description_string
            except Exception as error:
                logging.exception(error)
                error_message = f"Cannot set beam description {self._Beam.Description} to {beam_description_string}."
                rs_utils.raise_error(ErrorMessage=error_message, ExceptionError=error)

        return

    def RenameIsocenter(self, new_name):
        try:
            self._Beam.Isocenter.EditIsocenter(Name=new_name)
        except Exception as error:
            logging.exception(error)
            error_message = f"Cannot set beam {self._Beam.Name}'s isocenter name to {new_name}."
            rs_utils.raise_error(ErrorMessage=error_message, ExceptionError=error)
        return


# RayWindow comes from RayStation System package
class FieldNamerGUI(RayWindow):  # type: ignore
    field_namer_xaml = """<Window 
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="Field Namer" Height="290" Width="450">
    <Grid Margin="10,10,10,10">
        <Grid.ColumnDefinitions>
            <ColumnDefinition />
            <ColumnDefinition />
        </Grid.ColumnDefinitions>
        <Grid.RowDefinitions>
            <RowDefinition Height="30" />
            <RowDefinition Height="30" />
            <RowDefinition Height="30" />
            <RowDefinition Height="30" />
            <RowDefinition Height="60" />
            <RowDefinition Height="50" />
        </Grid.RowDefinitions>
        <TextBlock FontSize="16" FontWeight="Bold" Grid.Row="0" Grid.Column="0"    
                   Text="Field Type" />
        <TextBlock FontSize="16" FontWeight="Bold" Grid.Row="0" Grid.Column="1"   
                   Text="Starting Number" />

        <TextBlock Text="Treatment Fields" VerticalAlignment="Center" HorizontalAlignment="Left" Grid.Row="1" Grid.Column="0" FontSize="14"/>
        <TextBox Name="starting_tx_beam_number_input" TextAlignment="Right" VerticalAlignment="Center" HorizontalAlignment="Left" Grid.Row="1" Grid.Column="1"  TextWrapping="Wrap" Text="TextBox" Width="120" FontSize="14"/>

        <TextBlock Text="Setup Fields" VerticalAlignment="Center" HorizontalAlignment="Left" Grid.Row="2" Grid.Column="0" FontSize="14"/>
        <TextBox Name="starting_su_beam_number_input" TextAlignment="Right" VerticalAlignment="Center" HorizontalAlignment="Left" Grid.Row="2" Grid.Column="1"  TextWrapping="Wrap" Text="TextBox" Width="120" FontSize="14"/>

        <TextBlock Text="XVI" VerticalAlignment="Center" HorizontalAlignment="Left" Grid.Row="3" Grid.Column="0" FontSize="14"/>
        <TextBox Name="starting_xvi_beam_number_input" TextAlignment="Right" VerticalAlignment="Center" HorizontalAlignment="Left" Grid.Row="3" Grid.Column="1"  TextWrapping="Wrap" Text="TextBox" Width="120" FontSize="14"/>

        <TextBlock Text="Apply BeamSet Name to Isocenters" TextWrapping="Wrap" VerticalAlignment="Center" HorizontalAlignment="Left" Grid.Row="4" Grid.Column="0" FontSize="14" Width="205" Height="40"/>
        <CheckBox Name="rename_iso_input" VerticalAlignment="Center" HorizontalAlignment="Center" Grid.Row="4" Grid.Column="1" FontSize="14"/>

        <Button Name="submit" Click="SubmitClicked" Content="Submit" Grid.Row="5" Grid.Column="1" HorizontalAlignment="Left" VerticalAlignment="Top" RenderTransformOrigin="4.598,0.379" Width="53" Margin="0,25,0,0"/>
        <Button Name="cancel" Click="CancelClicked" Content="Cancel" Grid.Row="5" Grid.Column="1" HorizontalAlignment="Right"  VerticalAlignment="Top" Width="54" Margin="0,25,95,0"/>

    </Grid>

</Window>
"""

    def __init__(
        self,
        starting_tx_beam_number,
        starting_su_beam_number,
        starting_xvi_beam_number,
        rename_iso,
    ):
        """Initialize the GUI window with starting numbers"""
        self.LoadComponent(self.field_namer_xaml)
        self.starting_tx_beam_number_input.Text = str(starting_tx_beam_number)
        self.starting_su_beam_number_input.Text = str(starting_su_beam_number)
        self.starting_xvi_beam_number_input.Text = str(starting_xvi_beam_number)
        self.rename_iso_input.IsChecked = rename_iso

        # Set window as topmost window.
        self.Topmost = True

        # Start up window at the center of the screen. WindowStartUpLocation comes from RayStation System Package
        self.WindowStartupLocation = WindowStartupLocation.CenterScreen  # type: ignore

    def CancelClicked(self, sender, event):
        # Close window.
        self.DialogResult = False

    def SubmitClicked(self, sender, event):
        try:
            self.starting_tx_beam_number = int(self.starting_tx_beam_number_input.Text)
            self.starting_su_beam_number = int(self.starting_su_beam_number_input.Text)
            self.starting_xvi_beam_number = int(self.starting_xvi_beam_number_input.Text)
            self.rename_iso = self.rename_iso_input.IsChecked
        except Exception as error:
            logging.exception(error)
            error_message = f"Invalid input for one of the starting beam numbers."
            rs_utils.raise_error(ErrorMessage=error_message, ExceptionError=error)

        self.DialogResult = True


def main():
    patient = rs_utils.get_current_helper("Patient")
    plan = rs_utils.get_current_helper("Plan")
    beam_set = rs_utils.get_current_helper("BeamSet")

    # Wrap classes to include additional methods
    beam_set_wrapper = BeamSetWrapper(plan=plan, beam_set=beam_set)
    patient_wrapper = PatientWrapper(patient=patient, beam_set=beam_set)

    # Find best guesses for starting beam numbers to treatment/setup/cbct beams
    previous_tx_beam_names = [
        name for name in patient_wrapper.get_all_beam_names(beam_type="Treatment")
    ]
    previous_su_beam_names = [
        name for name in patient_wrapper.get_all_beam_names(beam_type="Setup")
    ]

    starting_tx_beam_number = patient_wrapper.guess_starting_beam_number(
        "(?<=A)?\d+(?=(?:B|$))", previous_tx_beam_names
    )
    starting_su_beam_number = patient_wrapper.guess_starting_beam_number(
        "(?<=SU)\d+", previous_su_beam_names
    )
    starting_xvi_beam_number = patient_wrapper.guess_starting_beam_number(
        "(?<=XVI)\d+", previous_su_beam_names
    )

    # Rename isocenter default option
    rename_iso = True

    field_namer_gui = FieldNamerGUI(
        starting_tx_beam_number, starting_su_beam_number, starting_xvi_beam_number, rename_iso
    )
    field_namer_gui.ShowDialog()

    # Get the starting numbers from the GUI
    if field_namer_gui.DialogResult:
        starting_tx_beam_number = field_namer_gui.starting_tx_beam_number
        starting_su_beam_number = field_namer_gui.starting_su_beam_number
        starting_xvi_beam_number = field_namer_gui.starting_xvi_beam_number
        rename_iso = field_namer_gui.rename_iso
    else:
        # Kill the script if we cancel the dialog box
        return

    # Using data from the gui, proceed with naming

    """
    Algorithm as follows:
    Get TX beams/Setup Beams list object
    Get the list of new names and descriptions using BeamSet Method, this list is made unique
    Use rename_my_beams BeamSet Method, this handles duplications if there are any
    """

    ### Treatment beams
    try:
        tx_beams = beam_set.Beams
    except Exception as error:
        logging.exception(error)
        error_message = f"Could not get beams for beam set {beam_set.DicomPlanLabel}."
        rs_utils.raise_error(ErrorMessage=error_message, ExceptionError=error)

    new_tx_beam_names_descriptions = beam_set_wrapper.get_new_beam_names_descriptions(
        tx_beams, starting_tx_beam_number
    )
    beam_set_wrapper.rename_my_beams(
        tx_beams, new_tx_beam_names_descriptions, rename_iso=rename_iso
    )

    ### Setup beams
    try:
        setup_beams = beam_set.PatientSetup.SetupBeams
    except Exception as error:
        logging.exception(error)
        error_message = f"Could not get setup beams for beam set {beam_set.DicomPlanLabel}."
        rs_utils.raise_error(ErrorMessage=error_message, ExceptionError=error)

    # find last_index to ignore the renaming the last setup beam
    last_index = len(setup_beams) - 1
    new_su_beam_names_descriptions = beam_set_wrapper.get_new_beam_names_descriptions(
        setup_beams, starting_su_beam_number
    )
    beam_set_wrapper.rename_my_beams(
        setup_beams,
        new_su_beam_names_descriptions,
        rename_iso=rename_iso,
        ignore_beam=[last_index],
    )

    ### Handle XVI fields separately
    # This is fairly hard coded, because there is no way to determine a CBCT field within the setup field itself

    xvi_index = last_index
    new_xvi_beam_name = f"XVI{starting_xvi_beam_number:02d}"
    new_xvi_beam_description = f"CB {beam_set.DicomPlanLabel}"

    # Create my own tuple for renaming
    new_xvi_beam_names_descriptions = [(xvi_index, new_xvi_beam_name, new_xvi_beam_description)]

    # Ignore index list
    ignore_su_beam_index = list(range(last_index))

    # Rename function
    beam_set_wrapper.rename_my_beams(
        setup_beams,
        new_xvi_beam_names_descriptions,
        rename_iso=rename_iso,
        ignore_beam=ignore_su_beam_index,
    )


if __name__ == "__main__":
    main()
