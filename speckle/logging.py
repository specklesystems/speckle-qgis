"""Logging Utility Module for Speckle QGIS"""
from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtWidgets import QPushButton


class Logging:
    """Holds utility methods for logging messages to QGIS"""

    qgisInterface = None

    def __init__(self, iface) -> None:
        self.qgisInterface = iface

    def logToUserWithAction(self, message: str, action_text:str, callback: bool, level: Qgis.MessageLevel = Qgis.Info, duration:int =10):
        if not self.qgisInterface:
            return
        widget = self.qgisInterface.messageBar().createMessage("Speckle", message)
        button = QPushButton(widget)
        button.setText(action_text)
        button.pressed.connect(callback)
        widget.layout().addWidget(button)
        self.qgisInterface.messageBar().pushWidget(widget, level, duration)

    def logToUser(self, message: str, level: Qgis.MessageLevel = Qgis.Info, duration: int =10):
        """Logs a specific message to the user in QGIS"""
        self.log(message, level)
        if self.qgisInterface:
            self.qgisInterface.messageBar().pushMessage(
                "Speckle", message, level=level, duration=duration
            )

    def log(self, message: str, level: Qgis.MessageLevel = Qgis.Info):
        """Logs a specific message to the Speckle messages panel."""
        QgsMessageLog.logMessage(message, "Speckle", level=level)


logger = Logging(None)
