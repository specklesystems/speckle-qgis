from qgis.core import Qgis, QgsMessageLog

class Logging:
    qgisInterface = None

    def __init__(self, iface) -> None:
        self.qgisInterface = iface
        
    def logToUser(self, message, level=Qgis.Info, duration=10):
        self.log(message,level)
        if(self.qgisInterface):
            self.qgisInterface.messageBar().pushMessage(
                "Speckle", message,
                level=level, duration=duration)

    def log(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'Speckle', level=level)

logger = Logging(None)