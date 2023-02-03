from System.Windows.Markup import XamlReader
from System.IO import StringReader
from System.Xml import XmlReader
from System.Windows import LogicalTreeHelper
from xml.etree import ElementTree
from io import StringIO
import re


class RayWindow():
    """
    Class to help with the transition from WPF in IronPython to CPython.#    
    """

    def __init__(self):
        self.window = None

    def __dir__(self):
        """
        Adds attributes from self.window to the output of dir() and to tab completion.
        Emulates inheritance from Window.
        """
        return super().__dir__() + dir(self.window)

    def __getattr__(self, name):
        """
        Enables getting of attributes from self.window directly on RayWindow.
        Emulates inheritance from Window.
        """
        if 'window' in self.__dict__:
            if hasattr(self.window, name):
                return getattr(self.window, name)
        # Gives default error message when attribute is not found.
        self.__getattribute__(name)

    def __setattr__(self, name, value):
        """
        Enables setting of attributes from self.window directly on RayWindow.
        Emulates inheritance from Window.
        """
        if 'window' in self.__dict__:
            if hasattr(self.window, name):
                setattr(self.window, name, value)
        self.__dict__[name] = value

    def LoadComponent(self, xaml):
        """
        Load a xaml string and connects its elements to this python object.
        """
        xaml, events, names = self._prepare_xaml(xaml)
        xr = XmlReader.Create(StringReader(xaml))
        self.window = XamlReader.Load(xr)
        self._connect_wpf_elements(names)
        self._connect_event_handlers(events)

    def _connect_wpf_elements(self, names):
        """
        Add C# elements to self.
        Use after xaml is loaded.
        """
        for name in names:
          if getattr(self, name, None) is not None:
              raise Exception("Class (\"{0}\") already has a field/function called \"{1}\" or element name \"{1}\" is used twice in the xaml.".format(self.__class__.__name__, name))
          setattr(self, name, LogicalTreeHelper.FindLogicalNode(self.window, name))

    def _prepare_xaml(self, xaml):
        """
        Get the name of all name and clicks of all elemets.
        Removes click="" from all elements.
        Use before loading xaml.
        """
        tree = ElementTree.fromstring(xaml)
        nsmap = {n[0]:n[1] for _,n in ElementTree.iterparse(StringIO(xaml),events=["start-ns"])}
        for k,v in nsmap.items():
            ElementTree.register_namespace(k, v)
        events = []
        names = []
        click_function_prefix ="CLICK_FUNCTION"
        known_events = ['Checked', 'Click', 'ContextMenuClosing', 'ContextMenuOpening', 'DataContextChanged', 'DpiChanged', 'DragEnter', 'DragLeave', 'DragOver', 'Drop', 'FocusableChanged',
            'GiveFeedback', 'GotFocus', 'GotKeyboardFocus', 'GotMouseCapture', 'GotStylusCapture', 'GotTouchCapture', 'Indeterminate', 'Initialized', 'IsEnabledChanged', 'IsHitTestVisibleChanged',
            'IsKeyboardFocusWithinChanged', 'IsKeyboardFocusedChanged', 'IsMouseCaptureWithinChanged', 'IsMouseCapturedChanged', 'IsMouseDirectlyOverChanged', 'IsStylusCaptureWithinChanged',
            'IsStylusCapturedChanged', 'IsStylusDirectlyOverChanged', 'IsVisibleChanged', 'KeyDown', 'KeyUp', 'LayoutUpdated', 'LoadCompleted', 'Loaded', 'LostFocus', 'LostKeyboardFocus',
            'LostMouseCapture', 'LostStylusCapture', 'LostTouchCapture', 'ManipulationBoundaryFeedback', 'ManipulationCompleted', 'ManipulationDelta', 'ManipulationInertiaStarting', 'ManipulationStarted',
            'ManipulationStarting', 'MessageHook', 'MouseDoubleClick', 'MouseDown', 'MouseEnter', 'MouseLeave', 'MouseLeftButtonDown', 'MouseLeftButtonUp', 'MouseMove', 'MouseRightButtonDown',
            'MouseRightButtonUp', 'MouseUp', 'MouseWheel', 'Navigated', 'Navigating', 'PreviewDragEnter', 'PreviewDragLeave', 'PreviewDragOver', 'PreviewDrop', 'PreviewGiveFeedback',
            'PreviewGotKeyboardFocus', 'PreviewKeyDown', 'PreviewKeyUp', 'PreviewLostKeyboardFocus', 'PreviewMouseDoubleClick', 'PreviewMouseDown', 'PreviewMouseLeftButtonDown', 'PreviewMouseLeftButtonUp',
            'PreviewMouseMove', 'PreviewMouseRightButtonDown', 'PreviewMouseRightButtonUp', 'PreviewMouseUp', 'PreviewMouseWheel', 'PreviewQueryContinueDrag', 'PreviewStylusButtonDown', 'PreviewStylusButtonUp',
            'PreviewStylusDown', 'PreviewStylusInAirMove', 'PreviewStylusInRange', 'PreviewStylusMove', 'PreviewStylusOutOfRange', 'PreviewStylusSystemGesture', 'PreviewStylusUp', 'PreviewTextInput',
            'PreviewTouchDown', 'PreviewTouchMove', 'PreviewTouchUp', 'QueryContinueDrag', 'QueryCursor', 'RequestBringIntoView', 'ScrollChanged', 'SelectionChanged', 'SizeChanged', 'SourceUpdated',
            'StylusButtonDown', 'StylusButtonUp', 'StylusDown', 'StylusEnter', 'StylusInAirMove', 'StylusInRange', 'StylusLeave', 'StylusMove', 'StylusOutOfRange', 'StylusSystemGesture', 'StylusUp',
            'TargetUpdated', 'TextChanged', 'TextInput', 'ToolTipClosing', 'ToolTipOpening', 'TouchDown', 'TouchEnter', 'TouchLeave', 'TouchMove', 'TouchUp', 'Unchecked', 'Unloaded']

        def get_from_any_ns(element, attribute, namespaces):
            for _, namespace in namespaces.items():
                value = element.get("{{{}}}{}".format(namespace, attribute))
                if value is not None:
                    return value
            return element.get(attribute)

        for elem in tree.iter():
            name = get_from_any_ns(elem, "Name", nsmap)
            if name is not None:
                names.append(name)

            events_on_element = [(x, get_from_any_ns(elem, x, nsmap),) for x in known_events if get_from_any_ns(elem, x, nsmap) is not None]
            for e in events_on_element:
                event, event_func = e
                if name is not None and event_func is not None:
                    events.append((name, event, event_func,))
                elif event_func is not None:
                    # Add a name to the element
                    name = click_function_prefix+event_func
                    elem.set("Name", name)
                    if not name in names:
                        names.append(name)
                    events.append((name, event, event_func,))
                elem.attrib.pop(event, None)
        xaml = ElementTree.tostring(tree, encoding="unicode", method="xml")
        return xaml, events, names

    def _connect_event_handlers(self, events):
        """
        Connect the python event handler to the wpf element.
        Use after _connect_wpf_elements()
        """
        for name, event, event_func in events:
            csharp_attr = getattr(self, name, None)
            print(name, event, event_func, csharp_attr)
            if csharp_attr is not None:
                e = getattr(csharp_attr, event, None)
                e += getattr(self, event_func, None)