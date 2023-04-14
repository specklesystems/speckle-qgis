# Example of embedding CEF browser using PyQt4, PyQt5 and
# PySide libraries. This example has two widgets: a navigation
# bar and a browser.
#
# Tested configurations:
# - PyQt 5.8.2 (qt 5.8.0) on Windows/Linux/Mac
# - PyQt 4.10.4 / 4.11.4 (qt 4.8.6 / 4.8.7) on Windows/Linux
# - PySide 1.2.1 (qt 4.8.6) on Windows/Linux/Mac
# - PySide2 5.6.0, 5.11.2 (qt 5.6.2, 5.11.2) on Windows/Linux/Mac
# - CEF Python v55.4+
#
# Issues with PySide 1.2:
# - Mac: Keyboard focus issues when switching between controls (Issue #284)
# - Mac: Mouse cursor never changes when hovering over links (Issue #311)

# https://github.com/cztomczak/cefpython/blob/5679f28cec18a57a56e298da2927aac8d8f83ad6/examples/qt.py#L360

import time
from cefpython3 import cefpython as cef
import ctypes
import os
import platform
import sys

# GLOBALS
PYQT4 = False
PYQT5 = False
PYSIDE = False
PYSIDE2 = False

PYQT5 = True
# noinspection PyUnresolvedReferences
from PyQt5.QtGui import *
# noinspection PyUnresolvedReferences
from PyQt5.QtCore import *
# noinspection PyUnresolvedReferences
from PyQt5.QtWidgets import *

# Fix for PyCharm hints warnings when using static methods
WindowUtils = cef.WindowUtils()

# Platforms
WINDOWS = (platform.system() == "Windows")
LINUX = (platform.system() == "Linux")
MAC = (platform.system() == "Darwin")

# Configuration
WIDTH = 800
HEIGHT = 600

# OS differences
CefWidgetParent = QWidget
if LINUX and (PYQT4 or PYSIDE):
    # noinspection PyUnresolvedReferences
    CefWidgetParent = QX11EmbedContainer

def main():
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    settings = {}

    cef.Initialize(settings)
    app = CefApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    main_window.activateWindow()
    main_window.raise_()
    app.exec_()
    if not cef.GetAppSetting("external_message_pump"):
        app.stopTimer()
    del main_window  # Just to be safe, similarly to "del app"
    del app  # Must destroy app object before calling Shutdown
    cef.Shutdown()
    return 


def check_versions():
    print("[qt.py] CEF Python {ver}".format(ver=cef.__version__))
    print("[qt.py] Python {ver} {arch}".format(
            ver=platform.python_version(), arch=platform.architecture()[0]))
    if PYQT4 or PYQT5:
        print("[qt.py] PyQt {v1} (qt {v2})".format(
              v1=PYQT_VERSION_STR, v2=qVersion()))
    elif PYSIDE:
        print("[qt.py] PySide {v1} (qt {v2})".format(
              v1=PySide.__version__, v2=QtCore.__version__))
    elif PYSIDE2:
        print("[qt.py] PySide2 {v1} (qt {v2})".format(
              v1=PySide2.__version__, v2=QtCore.__version__))
    # CEF Python version requirement
    assert cef.__version__ >= "55.4", "CEF Python v55.4+ required to run this"


class MainWindow(QMainWindow):
    def __init__(self):
        # noinspection PyArgumentList
        super(MainWindow, self).__init__(None)
        # Avoids crash when shutting down CEF (issue #360)
        #if PYSIDE:
        #    self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.cef_widget = None
        self.navigation_bar = None
        self.branchDropdown = None
        self.setWindowTitle("PyQt5 example")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setupLayout()

    def setupLayout(self):
        self.resize(WIDTH, HEIGHT)
        self.cef_widget = CefWidget(self)
        self.navigation_bar = NavigationBar(self.cef_widget)
        layout = QGridLayout()
        
        # populate branch dropdown
        if self.branchDropdown is None:
            self.branchDropdown = QComboBox()
        else: self.branchDropdown.clear()
        for item in ["new_design","land_use", "context_buildings"]:
            self.branchDropdown.addItem(item)
        label = QLabel("Select branch to overlay")

        widget = QWidget() 
        widget.layout = QHBoxLayout(widget)
        widget.layout.addWidget(label)
        widget.layout.addWidget(self.branchDropdown)
        widget.layout.addWidget(QLabel("   "))
        widget.layout.addWidget(QLabel("   "))
        layout.addWidget(widget, 0, 0)

        # noinspection PyArgumentList
        #layout.addWidget(self.navigation_bar, 0, 0)
        # noinspection PyArgumentList
        layout.addWidget(self.cef_widget, 1, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)


        # noinspection PyArgumentList
        frame = QFrame()
        frame.setLayout(layout)
        self.setCentralWidget(frame)

        self.show()

        # Browser can be embedded only after layout was set up
        self.cef_widget.embedBrowser()

    def closeEvent(self, event):
        return
        # Close browser (force=True) and free CEF reference
        if self.cef_widget.browser:
            self.cef_widget.browser.CloseBrowser(True)
            self.clear_browser_references()

    def clear_browser_references(self):
        # Clear browser references that you keep anywhere in your
        # code. All references must be cleared for CEF to shutdown cleanly.
        self.cef_widget.browser = None


class CefWidget(CefWidgetParent):
    def __init__(self, parent=None):
        # noinspection PyArgumentList
        super(CefWidget, self).__init__(parent)
        self.parent = parent
        self.browser = None
        self.hidden_window = None  # Required for PyQt5 on Linux
        self.show()

    def focusInEvent(self, event):
        # This event seems to never get called on Linux, as CEF is
        # stealing all focus due to Issue #284.
        if cef.GetAppSetting("debug"):
            print("[qt.py] CefWidget.focusInEvent")
        if self.browser:
            WindowUtils.OnSetFocus(self.getHandle(), 0, 0, 0)
            self.browser.SetFocus(True)

    def focusOutEvent(self, event):
        # This event seems to never get called on Linux, as CEF is
        # stealing all focus due to Issue #284.
        if cef.GetAppSetting("debug"):
            print("[qt.py] CefWidget.focusOutEvent")
        if self.browser:
            self.browser.SetFocus(False)

    def embedBrowser(self):
        window_info = cef.WindowInfo()
        rect = [0, 0, self.width(), self.height()]
        window_info.SetAsChild(self.getHandle(), rect)
        self.browser = cef.CreateBrowserSync(window_info,
                                             url="https://speckle.xyz/embed?stream=62973cd221&commit=ffc7f53f6a")
        self.browser.SetClientHandler(LoadHandler(self.parent.navigation_bar))
        self.browser.SetClientHandler(FocusHandler(self))

    def getHandle(self):
        if self.hidden_window:
            # PyQt5 on Linux
            return int(self.hidden_window.winId())
        try:
            # PyQt4 and PyQt5
            return int(self.winId())
        except:
            # PySide:
            # | QWidget.winId() returns <PyCObject object at 0x02FD8788>
            # | Converting it to int using ctypes.

            # Python 3
            ctypes.pythonapi.PyCapsule_GetPointer.restype = (
                    ctypes.c_void_p)
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = (
                    [ctypes.py_object])
            return ctypes.pythonapi.PyCapsule_GetPointer(
                    self.winId(), None)

    def moveEvent(self, _):
        self.x = 0
        self.y = 0
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSize(self.getHandle(), 0, 0, 0)
            elif LINUX:
                self.browser.SetBounds(self.x, self.y,
                                       self.width(), self.height())
            self.browser.NotifyMoveOrResizeStarted()

    def resizeEvent(self, event):
        size = event.size()
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSize(self.getHandle(), 0, 0, 0)
            elif LINUX:
                self.browser.SetBounds(self.x, self.y,
                                       size.width(), size.height())
            self.browser.NotifyMoveOrResizeStarted()


class CefApplication(QApplication):
    def __init__(self, args):
        super(CefApplication, self).__init__(args)
        if not cef.GetAppSetting("external_message_pump"):
            self.timer = self.createTimer()
        #self.setupIcon()

    def createTimer(self):
        timer = QTimer()
        # noinspection PyUnresolvedReferences
        timer.timeout.connect(self.onTimer)
        timer.start(10)
        return timer

    def onTimer(self):
        cef.MessageLoopWork()

    def stopTimer(self):
        # Stop the timer after Qt's message loop has ended
        self.timer.stop()

    def setupIcon(self):
        icon_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 "resources", "{0}.png".format(sys.argv[1]))
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))


class LoadHandler(object):
    def __init__(self, navigation_bar):
        self.initial_app_loading = True
        self.navigation_bar = navigation_bar

    def OnLoadStart(self, browser, **_):
        #self.navigation_bar.url.setText(browser.GetUrl())
        if self.initial_app_loading:
            #time.sleep(0.5)
            self.navigation_bar.cef_widget.setFocus()
            self.initial_app_loading = False

class FocusHandler(object):
    def __init__(self, cef_widget):
        self.cef_widget = cef_widget

    def OnTakeFocus(self, **_):
        if cef.GetAppSetting("debug"):
            print("[qt.py] FocusHandler.OnTakeFocus")

    def OnSetFocus(self, **_):
        if cef.GetAppSetting("debug"):
            print("[qt.py] FocusHandler.OnSetFocus")

    def OnGotFocus(self, browser, **_):
        if cef.GetAppSetting("debug"):
            print("[qt.py] FocusHandler.OnGotFocus")
        self.cef_widget.setFocus()
        # Temporary fix no. 1 for focus issues on Linux (Issue #284)
        if LINUX:
            browser.SetFocus(True)


class NavigationBar(QFrame):
    def __init__(self, cef_widget):
        # noinspection PyArgumentList
        super(NavigationBar, self).__init__()
        self.cef_widget = cef_widget

        # Init layout
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Url input
        #self.url = QLineEdit("")
        # noinspection PyUnresolvedReferences
        #self.url.returnPressed.connect(self.onGoUrl)

    def onReload(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.Reload()

    def onGoUrl(self):
        #time.sleep(0.5)
        url = "https://speckle.xyz/embed?stream=62973cd221&commit=ffc7f53f6a"
        if self.cef_widget.browser:
            self.cef_widget.browser.LoadUrl(url)

