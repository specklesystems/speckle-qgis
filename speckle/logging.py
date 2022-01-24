"""Logging Utility Module for Speckle QGIS"""
from qgis.core import Qgis, QgsMessageLog


class Logging:
    """Holds utility methods for logging messages to QGIS"""

    qgisInterface = None

    def __init__(self, iface) -> None:
        self.qgisInterface = iface

    def logToUser(self, message, level=Qgis.Info, duration=10):
        """Logs a specific message to the user in QGIS"""
        self.log(message, level)
        if self.qgisInterface:
            self.qgisInterface.messageBar().pushMessage(
                "Speckle", message, level=level, duration=duration
            )

    def log(self, message, level=Qgis.Info):
        """Logs a specific message to the Speckle messages panel."""
        QgsMessageLog.logMessage(message, "Speckle", level=level)


logger = Logging(None)
