from qgis.core import Qgis, QgsMessageLog


def logToUser(iface, message, level=Qgis.Info, duration=3):
    iface.messageBar().pushMessage(
        "Speckle", message,
        level=level, duration=duration)

def log(message, level=Qgis.Info):
    QgsMessageLog.logMessage(message, 'Speckle', level=level)