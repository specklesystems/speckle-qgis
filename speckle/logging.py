"""Logging Utility Module for Speckle QGIS"""
import inspect
from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtWidgets import QPushButton
from ui.logger import logToUser


class Logging:
    """Holds utility methods for logging messages to QGIS"""

    qgisInterface = None

    def __init__(self, iface) -> None:
        self.qgisInterface = iface

    def log(self, message: str, level: Qgis.MessageLevel = Qgis.Info):
        """Logs a specific message to the Speckle messages panel."""
        try:
            if level==0: level = Qgis.Info
            if level==1: level = Qgis.Warning
            if level==2: level = Qgis.Critical
            #return
            QgsMessageLog.logMessage(message, "Speckle", level=level)
        except Exception as e:
            try:
                logToUser(e, level = 2, func = inspect.stack()[0][3])
                return
            except: pass


    def logToUserWithAction(self, message: str, action_text:str, callback: bool, level: Qgis.MessageLevel = Qgis.Info, duration:int =10):
        return
        if not self.qgisInterface:
            return
        widget = self.qgisInterface.messageBar().createMessage("Speckle", message)
        button = QPushButton(widget)
        button.setText(action_text)
        button.pressed.connect(callback)
        widget.layout().addWidget(button)
        self.qgisInterface.messageBar().pushWidget(widget, level, duration)

    def logToUser(self, message: str, level: Qgis.MessageLevel = Qgis.Info, duration: int =10, func=None, plugin=None):
        """Logs a specific message to the user in QGIS"""
        return
        if level==Qgis.Info: level = 0
        if level==Qgis.Warning: level = 1
        if level==Qgis.Critical: level = 2

        logToUser(msg = message, level = level, func = func, plugin = plugin)
        return

        self.log(message, level)
        if self.qgisInterface:
            self.qgisInterface.messageBar().pushMessage(
                "Speckle", message, level=level, duration=duration
            )

logger = Logging(None)
