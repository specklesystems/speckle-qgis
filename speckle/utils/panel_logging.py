"""Logging Utility Module for Speckle QGIS"""
import inspect
from typing import Union
import webbrowser
from specklepy_qt_ui.qt_ui.logger import logToUser as logToUser_UI


def logToUser(
    msg: Union[str, Exception],
    func=None,
    level: int = 2,
    plugin=None,
    url="",
    blue=False,
    report=False,
):
    msg = str(msg)
    logToUser_UI(msg, func, level, plugin, url, blue, report)
    logger.writeToLog(msg.replace("\n", ". ") + " " + url, level, func)


class Logging:
    """Holds utility methods for logging messages to QGIS"""

    qgisInterface = None

    def __init__(self, iface) -> None:
        self.qgisInterface = iface

    def log(self, message: str, level: int = 0):
        """Logs a specific message to the Speckle messages panel."""
        try:
            from qgis.core import Qgis, QgsMessageLog

            if level == 0:
                level = Qgis.Info
            elif level == 1:
                level = Qgis.Warning
            elif level == 2:
                level = Qgis.Critical
            # return
            QgsMessageLog.logMessage(message, "Speckle", level=level)
        except ImportError:
            pass
        except Exception as e:
            try:
                logToUser(e, level=2, func=inspect.stack()[0][3])
            except:
                pass

    def btnClicked(url):
        try:
            if url == "":
                return
            webbrowser.open(url, new=0, autoraise=True)
        except Exception as e:
            pass

    def logToUserWithAction(
        self,
        message: str,
        action_text: str,
        url: str = "",
        level: int = 0,
        duration: int = 120,
    ):
        self.log(message, level)

        if not self.qgisInterface:
            return
        try:
            from qgis.core import Qgis
            from qgis.PyQt.QtWidgets import QPushButton

            if level == 0:
                level = Qgis.Info
            elif level == 1:
                level = Qgis.Warning
            elif level == 2:
                level = Qgis.Critical

            widget = self.qgisInterface.messageBar().createMessage("Speckle", message)
            button = QPushButton(widget)
            button.setText(action_text)
            button.pressed.connect(lambda: self.btnClicked(url))
            widget.layout().addWidget(button)
            self.qgisInterface.messageBar().pushWidget(widget, level, duration)
        except ImportError:
            pass

    def logToUserPanel(
        self,
        message: str,
        level: int = 0,
        duration: int = 20,
        func=None,
        plugin=None,
    ):
        """Logs a specific message to the user in QGIS"""

        self.log(message, level)

        if not self.qgisInterface:
            return
        try:
            from qgis.core import Qgis

            if level == 0:
                level = Qgis.Info
            if level == 1:
                level = Qgis.Warning
            if level == 2:
                level = Qgis.Critical

            if self.qgisInterface:
                self.qgisInterface.messageBar().pushMessage(
                    "Speckle", message, level=level, duration=duration
                )
        except ImportError:
            pass

    def writeToLog(self, msg: str = "", level: int = 2, func=None, plugin=None):
        msg = str(msg)
        if func is not None and func != "None":
            msg += "::" + str(func)
        self.log(msg, level)


logger = Logging(None)
