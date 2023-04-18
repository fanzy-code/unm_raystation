import os
import sys

import clr

import System

clr.AddReference("ScriptClient")
import traceback

import __builtin__
import ScriptClient


def connect(pid, base_addr="net.pipe://localhost/raystation_"):
    """Connect function for connecting to a scripting service host."""
    ScriptObjectHelp.replace_help()
    try:
        pid = str(pid)
        print("Connecting to RayStation. (Session id = " + pid + ")")
        uri = base_addr + pid
        ScriptClient.RayScriptService.Connect(uri)
    except System.Exception as e:
        print("!!! Script failed to connect to RayStation !!!")
        raise


class ScriptObjectHelp(object):
    """
    Class to modify the help function to provide customized help messages for
    RayStation objects. The modified help function prints the _help property
    of the RayStation classes and behaves as the built-in help on all other
    types. The built-in help is replaced by the modified help by calling the
    static method replace_help.
    """

    class __ScriptObjectHelp(object):
        """
        Modified help class which provides customized help messages for
        RayStation objects.
        """

        def __init__(self):
            """
            Creates a __ScriptObjectHelp object and stores the built-in help
            with it.
            """
            self.builtin_help = help  # The original help

        def __repr__(self):
            return self.builtin_help.__repr__()

        def __call__(self, *args, **kwds):
            """
            Implements custom help for RayStation objects, the original help
            for other objects, and help() with no arguments.
            """
            if not args:
                self.builtin_help(*args, **kwds)
            elif (
                isinstance(args[0], ScriptClient.ScriptObject)
                or isinstance(args[0], ScriptClient.ScriptMethod)
                or isinstance(args[0], ScriptClient.ScriptObjectCollection)
            ):
                # Print the documentation for RayStation objects.
                args[0]._help
            else:
                # All other objects are treated as in the built-in help.
                return self.builtin_help(*args, **kwds)

    """True if the built-in help has been replaced."""
    help_replaced = False

    @staticmethod
    def replace_help():
        """
        Replaces the built-in help with a modified help class.
        The function has no effect the second time it is called.
        """
        if not ScriptObjectHelp.help_replaced:
            # Replace the original help with this class.
            __builtin__.help = ScriptObjectHelp.__ScriptObjectHelp()
            ScriptObjectHelp.help_replaced = True


def get_current(objectType):
    """Get current object function."""
    if objectType == "ui" or objectType == "ui-recording" or objectType == "ui:Clinical":
        stop_if_no_gui("get_current(" + objectType + ")")
    return ScriptClient.ScriptObject(
        ScriptClient.RayScriptService.Instance,
        ScriptClient.RayScriptService.Instance.Client.GetCurrent(objectType),
    )


def await_user_input(message):
    """
    Unlock UI and wait for user input. The script will resume when the user
    presses continue.
    """
    stop_if_no_gui("await_user_input")
    ScriptClient.RayScriptService.Instance.Client.AwaitUserInput(message)


def is_gui_disabled():
    """
    Returns true if the creation of windows has been disabled, for
    example because the script is running on a server through RaaS.
    """
    return ScriptClient.RayScriptService.Instance.Client.IsGuiDisabled()


def stop_if_no_gui(methodName):
    """
    Raise an exception if the creation of windows has been disabled, for
    example because the script is running on a server through RaaS.
    """
    if ScriptClient.RayScriptService.Instance.Client.IsGuiDisabled():
        raise Exception(
            methodName + " has been disabled because the script is running with no GUI."
        )


def run(script, location="."):
    """Run a python script [from specified directory]."""
    check_path(location)
    if "." in script:
        raise Exception("Script name, '" + script + "', cannot contain a period.")
    if script in sys.modules:
        del sys.modules[script]
    saved_path = os.getcwd()
    append_path(saved_path)
    append_path(".")
    os.chdir(location)
    if is_autotest(script):
        import autotest_globals

        autotest_globals.import_autotest(
            script,
            location,
            os.path.join(os.path.dirname(autotest_globals.__file__), "AutoTesting"),
        )
    else:
        import imp

        fp, pathname, description = imp.find_module(script, [location])
        try:
            imp.load_source("__main__", pathname, fp)
        finally:
            if fp:
                fp.close()
    os.chdir(saved_path)


def check_path(location):
    """Checks directory path."""
    if not System.IO.Directory.Exists(location):
        raise Exception("Directory '" + location + "' does not exist.'")


def append_path(location):
    """Adds a directory to the PATH environment."""
    check_path(location)
    if not location in sys.path:
        sys.path.append(location)


def is_autotest(script):
    """Checks for tag in script name indicating RaySearch internal test script."""
    return script.endswith("@auto")


class CompositeAction:
    """
    The CompositeAction class is used to create an execution scope for sub-actions.
    It notifies the script service when the execution enters and exits the scope.
    By combining several actions in the scope of an CompositeAction they can be
    grouped and labeled as one action e.g. in the undo history.
    """

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        ScriptClient.RayScriptService.Instance.Client.CompositeActionCreated(self.name)

    def __exit__(self, type, value, traceback):
        if type is not None:
            has_error = True
            error_message = format_traceback()
        else:
            has_error = False
            error_message = None
        ScriptClient.RayScriptService.Instance.Client.CompositeActionDisposed(
            self.name, has_error, error_message
        )


def get_pid(name):
    """Alternative way of obtaining pid used when running RayStation autotests from Visual Studio."""
    pids = []
    a = os.popen("tasklist").readlines()  # Get all processes.

    # Look through all processes to find the wanted process and return the pid.
    for line in a:
        llist = line.split(" ")
        while True:
            try:
                llist.remove("")  # Remove empty strings from the list (there are a lot of them...)
            except:
                break  # Break while loop when all empty strings are removed.
        # Locate the correct process.
        if llist[0] == name:
            pid = llist[1]
            return pid
            break
    else:
        print("No pid found for process: %s" % name)
        return None


def format_error_message(heading):
    """
    Returns an error message with a heading specified by the caller. The error
    message consists of the specified heading followed by a traceback which
    excludes launch and connect.
    """
    trace_string_list = format_traceback()
    error_msg = heading + "\n\n" + trace_string_list
    error_msg = "\r\n".join(error_msg.splitlines())  # To get windows new-lines.
    return error_msg


def format_traceback():
    """
    Special stack trace info. Returns a list of strings similar to
    'traceback.format_exc()' but excludes launch and connect traceback for clarity.
    """
    try:
        (etype, value, tb) = sys.exc_info()
        tb_list = traceback.extract_tb(tb)
        if (
            len(tb_list) > 2
            and tb_list[0][0].endswith("launch.py")
            and tb_list[1][0].endswith("connect_ironpython.py")
        ):
            tb_list = tb_list[2:]
        result_list = ["Traceback (most recent call last):\n"]
        result_list = result_list + traceback.format_list(tb_list)
        return "".join(result_list)
    finally:
        etype = value = tb = None


def get_input():
    """
    Gets input string from the ScriptService in RayStation. Not used for user scripting.
    """
    return ScriptClient.RayScriptService.Instance.Client.GetInput()


def post_output(output_str):
    """
    Send a string that can be digested from the ScriptService in RayStation. Not used for user scripting.
    """
    ScriptClient.RayScriptService.Instance.Client.PostOutput(output_str)


def set_progress(message, percentage=-1, operation=None):
    """
    Send text and a percentage that should be used to set RayStation progress bar.
    It is also possible to specify an operation that has been performed. The operation
    is used to give RayCare users information about operations that have been performed
    by a script executed in RaaS through RayCare.
    """
    if percentage < -1 or 100 < percentage:
        raise ValueError("percentage must be between 0 and 100.")
    ScriptClient.RayScriptService.Instance.Client.SetProgress(message, percentage, operation)


# Connecting to RayStation
if not os.environ.has_key("RAYSTATION_PID"):
    # If the environment variable 'RAYSTATION_PID' is not set it might mean that a test script is being
    # run from Visual Studio.
    raystation_pid = get_pid("RayStation.exe")
    if raystation_pid:
        is_connected = False
        counter = 1
        while not is_connected:
            session_key = raystation_pid + "_" + str(counter)
            connect(session_key)
            try:
                get_current("ui")
                is_connected = True
                os.environ["RAYSTATION_PID"] = str(session_key)
            except SystemError:
                print(
                    "Could not connect to RayStation with current session ID (%s). Trying with a new session ID."
                    % session_key
                )
                counter += 1

            if counter > 10:
                print(
                    "Tried connecting to RayStation with a number of different session ids, but could not find the correct one. RayStation might need to be restarted."
                )
                break
    else:
        print("Did not connect to RayStation. The environment variable RAYSTATION_PID is not set!")
else:
    connect(os.environ["RAYSTATION_PID"])
