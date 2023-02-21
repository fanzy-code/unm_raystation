# mypy: ignore-errors
import ctypes

ctypes.windll.ole32.CoInitialize(
    None
)  # Must be done before importing clr, to set thread apartment state to STA for GUIs.
import clr

clr.AddReference("ScriptClient")
clr.AddReference("System.Runtime")
clr.AddReference("System.Runtime.InteropServices")

import ctypes
import inspect
import json
import os
import sys
import traceback

import numpy as np
import ScriptClient
import System
import System.Linq
from System import (
    Boolean,
    Byte,
    Double,
    Int16,
    Int32,
    Int64,
    IntPtr,
    SByte,
    Single,
    String,
    UInt16,
    UInt32,
    UInt64,
)
from System.Runtime.InteropServices import GCHandle, GCHandleType

if sys.version_info.major == 2:
    import __builtin__ as builtins  # Python 2
elif sys.version_info.major == 3:
    import builtins  # Python 3
else:
    raise Exception("Unknown Python version.")


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


def numpyify(src):
    """Converts numeric .NET arrays to numpy arrays."""
    elementType = src.GetType().GetElementType()
    if elementType.IsAssignableFrom(Boolean):
        npType = np.bool_
    elif elementType.IsAssignableFrom(Single):
        npType = np.float32
    elif elementType.IsAssignableFrom(Double):
        npType = np.float64
    elif elementType.IsAssignableFrom(SByte):
        npType = np.int8
    elif elementType.IsAssignableFrom(Int16):
        npType = np.int16
    elif elementType.IsAssignableFrom(Int32):
        npType = np.int32
    elif elementType.IsAssignableFrom(Int64):
        npType = np.int64
    elif elementType.IsAssignableFrom(Byte):
        npType = np.uint8
    elif elementType.IsAssignableFrom(UInt16):
        npType = np.uint16
    elif elementType.IsAssignableFrom(UInt32):
        npType = np.uint32
    elif elementType.IsAssignableFrom(UInt64):
        npType = np.uint64
    else:
        raise TypeError(
            "Cannot make numpy arrays from .NET array type %s" % (src.GetType().FullName,)
        )

    shape = tuple(src.GetLength(i) for i in range(src.Rank))

    dst = np.zeros(shape, dtype=npType)

    srchandle = GCHandle.Alloc(src, GCHandleType.Pinned)
    try:
        ctypes.memmove(dst.ctypes.data, srchandle.AddrOfPinnedObject().ToInt64(), dst.nbytes)
    finally:
        srchandle.Free()

    return dst


def arrayify(src):
    """
    Converts numpy arrays into numeric .NET arrays of the corresponding types.
    If the numpy arrays are multidimensional, the .NET arrays will also be
    multidimensional.
    """
    if src.dtype == np.bool:
        netType = Boolean
    elif src.dtype == np.float32:
        netType = Single
    elif src.dtype == np.float64:
        netType = Double
    elif src.dtype == np.int8:
        netType = SByte
    elif src.dtype == np.int16:
        netType = Int16
    elif src.dtype == np.int32:
        netType = Int32
    elif src.dtype == np.int64:
        netType = Int64
    elif src.dtype == np.uint8:
        netType = Byte
    elif src.dtype == np.uint16:
        netType = UInt16
    elif src.dtype == np.uint32:
        netType = UInt32
    elif src.dtype == np.uint64:
        netType = UInt64
    else:
        raise TypeError("Cannot make .NET arrays from numpy type %s" % (src.dtype))

    dst = System.Array.CreateInstance(netType, src.shape)

    src = np.ascontiguousarray(src)

    dsthandle = GCHandle.Alloc(dst, GCHandleType.Pinned)
    try:
        ctypes.memmove(dsthandle.AddrOfPinnedObject().ToInt64(), src.ctypes.data, src.nbytes)
    finally:
        dsthandle.Free()

    return dst


def systemify(src):
    """Converts numpy scalars into .NET types"""
    if isinstance(src, np.bool) or isinstance(src, np.bool_):
        return Boolean(src)
    elif isinstance(src, np.float32):
        return Single(src)
    elif isinstance(src, np.float64):
        return Double(src)
    elif isinstance(src, np.int8):
        return SByte(src)
    elif isinstance(src, np.int16):
        return Int16(src)
    elif isinstance(src, np.int32):
        return Int32(src)
    elif isinstance(src, np.int64):
        return Int64(src)
    elif isinstance(src, np.uint8):
        return Byte(src)
    elif isinstance(src, np.uint16):
        return UInt16(src)
    elif isinstance(src, np.uint32):
        return UInt32(src)
    elif isinstance(src, np.uint64):
        return UInt64(src)
    else:
        raise Exception("Unhandled numpy type " + type(src).__name__)


class ExpandoDictionary(dict):
    """
    Subclass of dictionary which also has the functionality of an
    ExpandoObject. The class converts an ExpandoObject to a dictionary which
    can be modified and passed back into RayStation. The class only copies
    data from the ExpandoObject and does update the ExpandoObject itself.
    Modifications to ExpandoObjects do not translate into changes in RayStation.
    """

    def __init__(self, expando):
        """
        Converts a System.Dynamic.ExpandoObject into an ExpandoDictionary.
        Members of the ExpandoObject are added as fields of the dictionary.
        """
        for element in expando:
            self[element.Key] = element.Value

    def __getattr__(self, name):
        """Makes it possible to get dictionary fields using dot syntax."""
        return self[name]

    def __setattr__(self, name, value):
        """Makes it possible to set dictionary fields using dot syntax."""
        self[name] = value

    def __dir__(self):
        """Adds the fields to the list of members."""
        members = dir(dict(self))
        members.extend(self.keys())
        return members


class sorted_dict(dict):
    """
    Subclass of dictionary which is converted to a
    System.Collections.Generic.SortedDictionary instead of a
    System.Collections.Generic.Dictionary when the object is passed to
    RayStation. A sorted_dict requires that all keys have the same type. The
    type is set when the dictionary is created. When new keys are added to the
    dictionary, they will be cast to the original key type.
    """

    """The .NET type for the keys in the dictionary."""
    key_type = None

    def __init__(self, d=None, key_type=None):
        """
        Creates a new sorted_dict.

        sorted_dict(x) converts a System.Collections.Generic.SortedDictionary into a sorted_dict.

        sorted_dict(key_type=System.Double) creates an empty sorted_dict where the
        keys are of type System.Double.
        """
        if key_type:
            if d:
                raise ValueError(
                    "The key_type input argument can only be specified when no other input arguments are given."
                )
            self.key_type = key_type
        else:
            if not isinstance(d, System.Object) or not d.GetType().Name.startswith(
                "SortedDictionary`"
            ):
                raise TypeError(
                    "The input argument must be a System.Collections.Generic.SortedDictionary."
                )
            self.key_type = d.GetType().GetGenericArguments()[0]
            for element in d:
                key = pyobjify(element.Key)
                value = pyobjify(element.Value)
                self[key] = value

    def __setitem__(self, key, value):
        """
        Overrides the setting of new elements. The new keys are converted to
        the key_type type, before the new element is inserted.
        """
        converted_key = System.Convert.ChangeType(key, self.key_type)
        dict.__setitem__(self, converted_key, value)


class array_list(list):
    """
    Subclass of list which is converted to an array instead of a list when the
    object is passed to RayStation. The constructor can either take no arguments
    and create an empty array_list, or take a .NET array as input and convert it
    into an array_list.
    """

    def __init__(self, l=None, p=False):
        if l == None:
            dict.__init__(self)
        else:
            if p:
                self.extend([pyobjify(element) for element in l])
            else:
                self.extend([element for element in l])


def pyobjify(x):
    """
    Converts .NET types to Python types. Some types, like System.DateTime and
    System.Drawing.Color are not converted.
    """
    if isinstance(x, list):
        return [pyobjify(y) for y in x]
    elif not isinstance(x, System.Object) and not isinstance(x, System.ValueType):
        # Already a Python type.
        return x
    elif isinstance(x, ScriptClient.CPythonScriptObject):
        return PyScriptObject(x)
    elif isinstance(x, ScriptClient.CPythonScriptObjectCollection):
        return PyScriptObjectCollection(x)
    elif isinstance(x, System.Array):
        elementType = x.GetType().GetElementType()
        if elementType.IsArray:
            return array_list(x, True)
        elif elementType.IsAssignableFrom(String):
            return array_list(x, False)
        elif elementType.Name == "CPythonScriptObject":
            return [PyScriptObject(y) for y in x]
        else:
            return numpyify(x)
    elif isinstance(x, ScriptClient.CPythonScriptMethod):
        return PyScriptMethod(x)
    elif isinstance(x, System.Dynamic.ExpandoObject):
        return ExpandoDictionary(x)
    elif x.GetType().Name.startswith("List`"):
        return [pyobjify(y) for y in x]
    elif x.GetType().Name.startswith("Dictionary`"):
        d = {}
        for element in x:
            key = pyobjify(element.Key)
            value = pyobjify(element.Value)
            d[key] = value
        return d
    elif x.GetType().Name.startswith("SortedDictionary`"):
        return sorted_dict(x)
    else:
        return x


def clrify(x):
    """
    Converts Python types into .Net types that can be passed to RayStation.
    Primitive data types are converted automatically when they are passed to
    RayStation. Lists are automatically converted to System arrays, but
    dictionaries are not converted.
    """
    if isinstance(x, PyScriptObject):
        return x._scriptObject
    elif isinstance(x, PyScriptObjectCollection):
        return x._scriptObjectCollection
    if isinstance(x, sorted_dict):
        retVal = System.Collections.Generic.SortedDictionary[System.Object, System.Object]()
        for k, v in x.items():
            retVal[clrify(k)] = clrify(v)
        return retVal
    if isinstance(x, dict):
        retVal = System.Collections.Generic.Dictionary[System.Object, System.Object]()
        for k, v in x.items():
            retVal[clrify(k)] = clrify(v)
        return retVal
    elif isinstance(x, array_list):
        if not x or clrify(x[0]) == x[0]:
            # This reduces the run time for types that do not need conversion.
            return System.Array[System.Object](x)
        else:
            return System.Array[System.Object]([clrify(y) for y in x])
    elif isinstance(x, list):
        # Convert the elements in lists, but keep them in a list.
        if not x or clrify(x[0]) == x[0]:
            # This reduces the run time for types that do not need conversion.
            return x
        else:
            return [clrify(y) for y in x]
    elif isinstance(x, np.ndarray):
        return arrayify(x)
    elif type(x).__module__ == "numpy":
        return systemify(x)
    else:
        return x


class ScriptObjectHelp(object):
    """
    Class to modify the help function to provide customized help messages for
    Python classes that wrap objects created in C#. The built-in help function
    gives information about the wrapper class and not about the wrapped class
    which it is meant to emulate. The modified help function class does the
    opposite, and behaves as the built-in help on all other types. Objects of
    the classes PyScriptObject and PyScriptMethod also have the property _help
    which gives the same help message. The built-in help is replaced by the
    modified help by calling the static method replace_help.
    """

    class __ScriptObjectHelp(object):
        """
        Modified help class which provides customized help messages for
        Python classes that wrap objects created in C#.
        """

        def __init__(self):
            """
            Creates a __ScriptObjectHelp object and replaces the built-in
            help with it.
            """
            self.builtin_help = help  # The original help

        def __repr__(self):
            return self.builtin_help.__repr__()

        def __call__(self, *args, **kwds):
            """
            Implements custom help for Python classes that wrap C# objects, and
            the original help for other classes and help() with no arguments.
            """
            if not args:
                self.builtin_help(*args, **kwds)
            elif isinstance(args[0], PyScriptObject) or isinstance(args[0], PyScriptMethod):
                # Print the documentation for script objects and script methods.
                args[0]._help
            elif isinstance(args[0], PyScriptObjectCollection):
                # Print the documentation for script object collections.
                print(args[0].__doc__)
            else:
                # All other classes behave the same as in the built-in help.
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
            builtins.help = ScriptObjectHelp.__ScriptObjectHelp()
            ScriptObjectHelp.help_replaced = True


def len(obj):
    """
    Redefines the len function which returns the number of elements in a
    container. The function behaves the same as the built-in function for all
    types that support the len function. For other types, the function returns
    the Count property if there is one. This makes it possible to get the
    length of System containers using by calling len.

    TODO: Remove this once all containers are converted into Python types.
    """
    try:
        return builtins.len(obj)
    except TypeError as e:
        # The type does not support the len function.
        if hasattr(obj, "Count"):
            # Use the Count parameter instead if there is one.
            return obj.Count
        else:
            raise e


class PyScriptObject(object):
    """
    Python wrapper for the CPythonScriptObject class. The class keeps the
    CPythonScriptObject as a member and passes function calls and returns outputs
    from that object.
    """

    """Returns True if two PyScriptObjects correspond to the same CompositeObject in RayStation."""

    def Equals(self, obj):
        return self._scriptObject.Equals(obj._scriptObject)

    def __init__(self, scriptObject):
        self._scriptObject = scriptObject

    @property
    def __doc__(self):
        """Documentation for the specific CPythonScriptObject type."""
        return self._scriptObject.GetMember("__doc__")

    def __getattr__(self, name):
        """
        Overrides attribute access so that members of the CPythonScriptObject
        become attributes.
        """
        try:
            x = self._scriptObject.GetMember(name)
        except System.Exception as e:
            if e.Message.startswith("Object has no member"):
                # In Python 3, hasattr requires that the thrown exception is an AttributeError.
                # Otherwise, an exception is thrown every time hasattr is called.
                raise AttributeError(e.Message)
            else:
                raise e
        return pyobjify(x)

    def __setattr__(self, name, value):
        """
        Overrides attribute modification so that members of the
        CPythonScriptObject can be set.
        """
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._scriptObject.SetMember(name, clrify(value))

    def __dir__(self):
        """Makes the dir command print the members of the CPythonScriptObject."""
        return list(self._scriptObject.GetMemberNames())

    @property
    def _help(self):
        """Prints a help message about the object."""
        if inspect.stack()[1][3] != "attr_matches":
            # The documentation should not be printed when pyreadline performs tab completion.
            print(self.__doc__)

    def __repr__(self):
        """
        Specifies the description which is printed when an object is entered
        in a Python terminal. This makes it possible to see the type of the
        CPythonScriptObject.

        TODO: Create a better description.
        """
        return self._scriptObject.__repr__()


class PyScriptValueIterator(object):
    """
    Iterator over PyScriptObjects in a PyScriptObjectCollection.
    This is the default iterator of the PyScriptObjectCollection class.
    """

    def __init__(self, collection):
        self.collection = collection
        self.index = 0

    def __next__(self):
        # Python 3
        if self.index >= len(self.collection):
            raise StopIteration

        ret = self.collection[self.index]
        self.index = self.index + 1
        return ret

    def next(self):
        # Python 2
        return self.__next__()

    def __iter__(self):
        return self


class PyScriptObjectCollection(object):
    """
    Python wrapper for the CPythonScriptObjectCollection class. The wrapper has the
    CPythonScriptObjectCollection object as a property and return its elements as
    PyScriptObjects. Objects in the collection can be retrieved using both
    indices and keys (for example patient.Cases[0] or patient.Cases["CASE 1"]).
    It is also possible to access elements using dot syntax, by adding an
    underscore and replacing spaces by underscores (for example
    patient.Cases._CASE_1). The last syntax allows tab completion. The property
    _help is not defined, because there could be an item called 'help' which would
    then be ambiguous.
    """

    def __init__(self, scriptObjectCollection):
        self._scriptObjectCollection = scriptObjectCollection

    @property
    def __doc__(self):
        """
        Documentation of PyScriptObjectCollection.
        TODO: Describe available members
        """
        doc_str = (
            "--------------------------------------------------------------------------\n"
            + "Help on CPythonScriptObjectCollection\n"
            + "--------------------------------------------------------------------------\n"
        )
        return doc_str

    def __contains__(self, pyScriptObject):
        """Checks if a PyScriptObject is in the collection."""
        return self._scriptObjectCollection.Contains(pyScriptObject._scriptObject)

    def __dir__(self):
        """Lists the members (and elements) of the CPythonScriptObjectCollection."""
        return list(self._scriptObjectCollection.GetMemberNames())

    def __getattr__(self, name):
        """Implements the dot syntax for access of elements."""
        x = self._scriptObjectCollection.GetMember(name)
        return pyobjify(x)

    def __getitem__(self, key):
        """Implements indexing using indices and keys."""
        x = self._scriptObjectCollection[key]
        return pyobjify(x)

    def __len__(self):
        """Makes the len function return the number of elements."""
        return self._scriptObjectCollection.Count

    def __iter__(self):
        """
        Returns an iterator over the elements in the collection.
        This makes it possible to use the syntaxes "for x in collection" and
        "for key, value in enumerate(collection)".
        """
        return PyScriptValueIterator(self)

    def has_key(self, key):
        """Checks if a key is present in the collection."""
        return key in self.keys

    def keys(self):
        """Returns a list of strings with the keys."""
        return self.Keys()

    def values(self):
        """
        Returns a list with the PyScriptObjects in the collection. The order
        is the same as the order of the keys returned by keys().
        """
        value_list = []
        for k in self.keys:
            value_list.append(self.__getitem__(k))
        return value_list

    def IndexOf(self, pyScriptObject):
        """Returns the index of a PyScriptObject in the collection."""
        return self._scriptObjectCollection.IndexOf(pyScriptObject._scriptObject)

    def KeyOf(self, pyScriptObject):
        """Returns the index of a PyScriptObject in the collection."""
        return self._scriptObjectCollection.KeyOf(pyScriptObject._scriptObject)

    def Contains(self, pyScriptObject):
        """
        The same as __contains__(), but with a syntax that matches the old
        syntax in IronPython.
        TODO: Consider removing this.
        """
        return self._scriptObjectCollection.Contains(pyScriptObject._scriptObject)

    @property
    def Keys(self):
        """
        The same as keys(), but with a syntax that matches the old
        syntax in IronPython.
        TODO: Consider removing this.
        """
        return list(self._scriptObjectCollection.Keys)

    @property
    def Count(self):
        """
        Returns the number of elements in the collection. The number of
        elements can also be retrieved using the len function, but this
        property matches the old syntax in IronPython.
        TODO: Consider removing this.
        """
        return self._scriptObjectCollection.Count

    def __repr__(self):
        # TODO: Create a better description.
        return "CPythonScriptObjectCollection with " + str(len(self)) + " elements"


class PyScriptMethod(object):
    """
    Python wrapper for the CPythonScriptMethod class. The class keeps the
    CPythonScriptMethod as a member and passes function calls and returns outputs
    from that object.
    """

    def __init__(self, scriptMethod):
        self._scriptMethod = scriptMethod

    @property
    def __doc__(self):
        return self._scriptMethod.GetMember("_help")

    def __call__(self, *args, **kwargs):
        if len(args) > 0:
            raise TypeError("Method must be called with named arguments.")
        # If one of the input arguments is a list that contains numpy values but has a first
        # element which is not a numpy value, the following error will occur:
        # "Error: value cannot be converted to Object."
        vals = System.Array[System.Object]([clrify(y) for y in kwargs.values()])
        keys = System.Array[System.String]([y for y in kwargs.keys()])
        return pyobjify(self._scriptMethod.Invoke(keys, vals))

    @property
    def _help(self):
        """Prints a help message about the object."""
        print(self.__doc__)

    def __repr__(self):
        """
        Specifies the description which is printed when an object is entered
        in a Python terminal.
        TODO: Create a better description.
        """
        return self._scriptMethod.GetMember("_")


def get_current(objectType):
    """
    Gets the current RayStation object of a specific type. The supported types are
    "Patient", "Case", "Plan", "BeamSet", "Examination", "PatientDB" and
    "MachineDB". The function returns a PyScriptObject.
    """
    if objectType == "ui" or objectType == "ui-recording" or objectType == "ui:Clinical":
        stop_if_no_gui("get_current(" + objectType + ")")
    return PyScriptObject(
        ScriptClient.CPythonScriptObject(
            ScriptClient.RayScriptService.Instance,
            ScriptClient.RayScriptService.Instance.Client.GetCurrent(objectType),
        )
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
    """Run a python script [from a specified directory]."""
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
        os.chdir(saved_path)
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
    """Adds a directory to the PATH environment variable."""
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
    By combining several actions in the scope of a CompositeAction they can be
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


class ClientCertificate:
    """
    RayCare client certificate used when RayCare scripting communicates with RayCare.
    The client certificate consists of a pfx-file with an encrypted X509 certificate,
    and a password for that file. The file is deleted when this object is disposed.
    """

    def __init__(self):
        client_certificate_dict = (
            ScriptClient.RayScriptService.Instance.ExportRayCareClientCertificate()
        )
        self.path = client_certificate_dict["path"]
        self.password = client_certificate_dict["password"]

    def __del__(self):
        try:
            os.remove(self.path)
        except:
            print("Unable to remove %s" % self.path)


class RayCareContextData:
    """
    Input argument class to RayCareContext in the RayCare Python package.
    Used to run RayCare scripting from a RayStation script.
    The RayCareContext makes it possible to modify the specified patient in RayCare.
    When a new patient is loaded, all old RayCareContextData objects will become invalid
    and throw exceptions if methods on them are called.
    A RayCareContextData object is connected to a specific case, but it is possible to have
    multiple RayCareContextData objects for different cases in parallel.
    """

    """Client certificate shared by all RayCareContexts."""
    _client_certificate = None

    """
    Creates a RayCareContextData object for a specific patient and case.
    The object becomes invalid if a different patient is loaded.
    """

    def __init__(self, patient, case=None):
        self.patient = patient
        self.__stop_if_not_current_patient__()
        episode_of_care_name = case.EpisodeOfCare.Name if case and case.EpisodeOfCare else None
        self.RayCare_keys = (
            ScriptClient.RayScriptService.Instance.GetRayCareScriptKeysForCurrentPatient(
                episode_of_care_name
            )
        )
        if RayCareContextData._client_certificate is None:
            RayCareContextData._client_certificate = ClientCertificate()

    """Returns the URI of the RayCare configuration endpoint."""

    def get_configuration_end_point_address(self):
        self.__stop_if_not_current_patient__()
        return ScriptClient.RayScriptService.Instance.GetRayCareConfigurationEndpointAddress()

    """Returns a patient specific RayCare token for HTTP authorization."""

    def get_token(self):
        self.__stop_if_not_current_patient__()
        return ScriptClient.RayScriptService.Instance.GetRayCareTokenForCurrentPatient()

    """Returns a RayCare key identifying the patient."""

    def get_patient_key(self):
        self.__stop_if_not_current_patient__()
        return self.RayCare_keys["patient_key"]

    """Returns a RayCare key identifying the workflow of the patient."""

    def get_workflow_key(self):
        self.__stop_if_not_current_patient__()
        return self.RayCare_keys["workflow_key"]

    """
    Returns a RayCare key identifying the episode of care which corresponds to the case
    for which the RayCareContextData object was created.
    """

    def get_episode_of_care_key(self):
        self.__stop_if_not_current_patient__()
        if not self.RayCare_keys["episode_of_care_key"]:
            raise Exception(
                "This functionality requires a case and is therefore only available in RayCare scripting "
                + "from RayStation when RayCareContextData is initialized with a case."
            )
        return self.RayCare_keys["episode_of_care_key"]

    """
    When a RayStation script is started from RayCare, this method returns a RayCare key
    identifying the task which started the script.
    The method raises an exception when the script is started from RayStation.
    """

    def get_task_key(self):
        self.__stop_if_not_current_patient__()
        task_key = self.RayCare_keys["task_key"]
        if not task_key:
            raise Exception(
                "This functionality requires a task key and is therefore only available in RayCare scripting "
                + "from RayStation when the script has been stared by a RayCare task."
            )
        return self.RayCare_keys["task_key"]

    def get_session_id(self):
        self.__stop_if_not_current_patient__()
        raise Exception(
            "This functionality is not available in RayCare scripting from RayStation because there is no session id."
        )

    def get_run_id(self):
        self.__stop_if_not_current_patient__()
        raise Exception(
            "This functionality is not available in RayCare scripting from RayStation because there is no run id."
        )

    """Returns the path of an encrypted pfx-file with a client certificate."""

    def get_client_certificate_path(self):
        self.__stop_if_not_current_patient__()
        return RayCareContextData._client_certificate.path

    """Returns the password of the client certificate pfx-file."""

    def get_client_certificate_password(self):
        self.__stop_if_not_current_patient__()
        return RayCareContextData._client_certificate.password

    """Used to crash the script when a RayCareContext for an old patient is used."""

    def __stop_if_not_current_patient__(self):
        if not self.patient.Equals(get_current("Patient")):
            raise Exception(
                "Invalid RayCareContext. The object is not associated with the current patient."
            )


def get_pid(name):
    """Alternative way of obtaining pid used when running RayStation autotests from Visual Studio."""
    pids = []
    a = os.popen("tasklist").readlines()  # Get all processes

    # Look through all processes to find the wanted process and return the pid.
    for line in a:
        llist = line.split(" ")
        while True:
            try:
                llist.remove("")  # Remove empty strings from the list (there are a lot of them...)
            except:
                break  # Break while loop when all empty strings are removed
        # Locate the correct process
        if llist[0] == name:
            pid = llist[1]
            return pid
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
            and tb_list[1][0].endswith("connect_cpython.py")
        ):
            tb_list = tb_list[2:]
        result_list = ["Traceback (most recent call last):\n"]
        result_list = result_list + traceback.format_list(tb_list)
        return "".join(result_list)
    finally:
        etype = value = tb = None


def get_input():
    """
    Gets input string from the ScriptService in RayStation. Not used for RayStation user scripting.
    """
    return ScriptClient.RayScriptService.Instance.Client.GetInput()


def post_output(output_str):
    """
    Send a string that can be digested from the ScriptService in RayStation. Not used for RayStation user scripting.
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
    ScriptClient.RayScriptService.Instance.Client.SetProgress(
        clrify(message), clrify(percentage), clrify(operation)
    )


def convert_python_list_to_cs_list(py_list, output_type=None):
    """
    Takes a python list and returns a C# list with the same elements.
    """
    if output_type is None and len(py_list) == 0:
        output_type = System.Object
    elif output_type is None and len(py_list) > 0:
        output_type = type(py_list[0])

    cs_list = System.Collections.Generic.List[output_type]()
    for e in py_list:
        cs_list.Add(e)
    return cs_list


def main():
    # Connecting to RayStation
    if "RAYSTATION_PID" not in os.environ:
        # If the environment variable 'RAYSTATION_PID' is not set it might mean
        # that a test script is being run from Visual Studio.
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
                        "Tried connecting to RayStation with a number of different session ids, "
                        + "but could not find the correct one. RayStation might need to be restarted."
                    )
                    break
        else:
            print(
                "Did not connect to RayStation. The environment variable RAYSTATION_PID is not set!"
            )
    else:
        connect(os.environ["RAYSTATION_PID"])


if __name__ == "__main__":
    main()
