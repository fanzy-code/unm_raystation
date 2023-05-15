""" 
Utility functions to assist with other RayStation Scripts.  Not meant to be ran on its own.

Installation:
Import, save, and validate this script in RayStation, ideally hidden from the clinical user.
Make sure to choose the appropriate environment so imports will work.

TODO:
...

"""

__author__ = "Michael Fan"
__contact__ = "mfan1@unmmg.org"
__version__ = "2.0.0"
__license__ = "MIT"


import html
import re
import unicodedata
from typing import Any, Optional

# RayStation API
import System
from connect import PyScriptObject, RayWindow, get_current
from System.Windows import *  # type: ignore
from System.Windows.Controls import *  # type: ignore


class ErrorWindow(RayWindow):
    """WPF window to display error messages, allow user to copy error message to clipboard."""

    def __init__(self, error_message: str, rs_exception_error: str):
        """Initialize the window."""
        xaml = """
        <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" 
                        Title="Error message" Height="425" Width="700">
            <Grid Margin="10,10,10,10">
                <Grid.RowDefinitions>
                    <RowDefinition Height="100" />
                    <RowDefinition Height="200" />
                    <RowDefinition Height="Auto" />
                </Grid.RowDefinitions>
                <Grid Grid.Row="0" Margin="15,15,15,15">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                    </Grid.ColumnDefinitions>
                    <TextBox Name="error_message" Grid.Column="0" HorizontalAlignment="Stretch" VerticalAlignment="Stretch" Margin="10" TextWrapping="Wrap" Text="Placeholder" ScrollViewer.VerticalScrollBarVisibility="Auto" Width="Auto" Height="Auto"/>
                </Grid>
                <Grid Grid.Row="1" Margin="15,15,15,15">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                    </Grid.ColumnDefinitions>
                    <Grid.RowDefinitions>
                        <RowDefinition Height="Auto" />
                        <RowDefinition Height="*" />

                    </Grid.RowDefinitions>
                    <Grid Grid.Row="0">
                        <TextBlock Name="traceback_textblock" Grid.Column="0" HorizontalAlignment="Stretch" VerticalAlignment="Stretch" Margin="10" TextWrapping="Wrap" Text="Error traceback" Width="Auto" Height="Auto"/>
                    </Grid>
                    <Grid Grid.Row="1">
                        <TextBox Name="traceback_message" Grid.Column="0" HorizontalAlignment="Stretch" VerticalAlignment="Stretch" Margin="10" TextWrapping="Wrap" Text="Placeholder" ScrollViewer.VerticalScrollBarVisibility="Auto" Width="Auto" Height="Auto"/>
                    </Grid>
                </Grid>
                <Grid Grid.Row="2" Margin="15,15,15,15">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                    </Grid.ColumnDefinitions>
                    <Button Width="50" Height="25" Name="cancel" Click="CancelClicked" Content="Close" Grid.Column="0" HorizontalAlignment="Center" VerticalAlignment="Center"/>
                </Grid>
            </Grid>
        </Window>
        """

        self.LoadComponent(xaml)

        self.error_message.Text = html.escape(error_message)  # type: ignore
        self.traceback_message.Text = str(rs_exception_error)  # type: ignore

    def CancelClicked(self, sender, event) -> None:
        # Close window.
        self.DialogResult = False
        return


def raise_error(error_message: str, rs_exception_error: Any, terminate=False) -> None:
    """
    Returns a GUI error message and the RayStation exception error for traceback

    Args:
        error_message (str): Custom error message
        rs_exception_error (Exception): Exception error passed

    """

    error_window = ErrorWindow(error_message, rs_exception_error)
    error_window.ShowDialog()  # type: ignore

    if terminate:
        raise Exception(error_message, rs_exception_error)
    return


def get_current_helper(input: str) -> PyScriptObject:
    """
    Helper function for connect.get_current function from RayStation.
    Added error logging and messaging.

    Args:
        input (str): Supported inputs are "Patient", "Case", "Plan", "BeamSet", "Examination", "PatientDB", "MachineDB", "ClinicDB"

    Returns:
        PyScriptObject: The called class object
    """

    supported_types = [
        "Patient",
        "Case",
        "Plan",
        "BeamSet",
        "Examination",
        "PatientDB",
        "MachineDB",
        "ClinicDB",
    ]

    if input not in supported_types:
        error_message = f"{input} is not in supported types: {supported_types}."
        raise ValueError(error_message)

    try:
        output = get_current(input)
        return output
    except Exception as rs_exception_error:
        error_message = f"{input} could not be loaded."
        raise_error(
            error_message=error_message, rs_exception_error=rs_exception_error, terminate=False
        )
        raise Exception(error_message, rs_exception_error)


def save_patient(patient: PyScriptObject) -> None:
    """
    Helper function for Patient.Save() function from Raystation.
    Patient class required as input, checks if modifications are made and saves the patient if so.

    Args:
        patient (PyScriptObject): patient object from RayStation API

    Returns:
        None

    """

    if patient.ModificationInfo == None:
        try:
            patient.Save()  # type: ignore
        except Exception as rs_exception_error:
            error_message = "Unable to save patient."
            raise_error(
                error_message=error_message, rs_exception_error=rs_exception_error, terminate=True
            )
    return


def slugify(value: str, allow_unicode: bool = False) -> str:
    """
    Django's function for sanitizing strings for filenames and URLs.  Gold standard for making
    input strings URL and filename friendly.

    Modified to keep case instead of making everything lower case.

    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.

    Args:
        value (str): input string
        allow_unicode (bool, optional): See above. Defaults to False.

    Returns:
        str: string sanitized for safe URLs and file paths
    """

    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[-\s]+", "-", value).strip("-_")


if __name__ == "__main__":
    test_error = "This script is not meant to be run directly!  This script contains helper functions for other scripts."
    test_exception_message = Exception
    raise_error(test_error, test_exception_message)
