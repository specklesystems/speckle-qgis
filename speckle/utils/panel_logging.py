"""Logging Utility Module for Speckle QGIS"""
import inspect
from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtWidgets import QPushButton
from specklepy_qt_ui.qt_ui.logger import logToUser as logToUser_UI
import webbrowser

def logToUser(msg: str, func=None, level: int = 2, plugin = None, url = "", blue = False):
    logToUser_UI(msg, func, level, plugin, url, blue)
    logger.writeToLog(msg.replace('\n', '. ') + " " + url, level, func)

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


    def logToUserWithAction(self, message: str, action_text:str, url: str = "", level: Qgis.MessageLevel = Qgis.Info, duration:int =120):
        
        self.log(message, level)

        if not self.qgisInterface:
            return
        
        if level==0: level = Qgis.Info
        if level==1: level = Qgis.Warning
        if level==2: level = Qgis.Critical
        
        def openLink(url):
            try:
                if url == "": return
                webbrowser.open(url, new=0, autoraise=True)
            except Exception as e: 
                pass 

        widget = self.qgisInterface.messageBar().createMessage("Speckle", message)
        button = QPushButton(widget)
        button.setText(action_text)
        button.pressed.connect(lambda: openLink(url))
        widget.layout().addWidget(button)
        self.qgisInterface.messageBar().pushWidget(widget, level, duration)


    def logToUser(self, message: str, level: Qgis.MessageLevel = Qgis.Info, duration: int =10, func=None, plugin=None):
        return
    
    def logToUserPanel(self, message: str, level: Qgis.MessageLevel = Qgis.Info, duration: int =20, func=None, plugin=None):
        """Logs a specific message to the user in QGIS"""

        self.log(message, level)
        
        if not self.qgisInterface: return
        
        if level==0: level = Qgis.Info
        if level==1: level = Qgis.Warning
        if level==2: level = Qgis.Critical
        
        if self.qgisInterface:
            self.qgisInterface.messageBar().pushMessage(
                "Speckle", message, level=level, duration=duration
            )
    
    def writeToLog(self, msg: str = "", level: int = 2, func=None, plugin=None):
        msg = str(msg)
        if func is not None: 
            msg += "::" + str(func)
        self.log(msg, level)

logger = Logging(None)
