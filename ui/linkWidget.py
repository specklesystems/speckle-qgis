
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, QTranslator, QRect, QObject
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget, QPushButton
from qgis.PyQt import QtWidgets
import webbrowser

import inspect

from ui.logger import logToUser 
from speckle.logging import logger

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

class LinkWidget(QWidget):
    
    # constructor
    def __init__(self, parent=None):
        super(LinkWidget, self).__init__(parent)
        print("start LinkWidget")
        self.parentWidget = parent
        self.btn = None
        print(self.parentWidget)
        # create a temporary floating button 
        width = 0 #parent.frameSize().width()
        height = 0# parent.frameSize().height()
        backgr_color = f"background-color: rgb{str(SPECKLE_COLOR)};"
        backgr_color_light = f"background-color: rgb{str(SPECKLE_COLOR_LIGHT)};"
        
        self.layout = QVBoxLayout(self)

        
        self.layout.setContentsMargins(0, 0, 0, 20)
        self.layout.setAlignment(Qt.AlignBottom)  
        self.setGeometry(0, 0, width, height)
        #self.mouseReleaseEvent = lambda event: self.closeLinkWidget(parent)

        button = QPushButton(f"👌 Data sent \n View it online") # to '{streamName}' Sent , v
        button.setStyleSheet("QPushButton {color: white;border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{backgr_color}" + "} QPushButton:hover { "+ f"{backgr_color_light}" + " }")

        self.layout.addWidget(button) #, alignment=Qt.AlignCenter) 
        button.clicked.connect(lambda: self.openLink())
        self.btn = button
        

    # overriding the mouseReleaseEvent method
    def mouseReleaseEvent(self, event):
        print("Mouse Release Event")
        self.parentWidget.hideLink()

    def openLink(self, url = ""):
        try:
            if url == "": 
                url = self.parentWidget.link_url
            webbrowser.open(url, new=0, autoraise=True)
            self.parentWidget.hideLink()
        except Exception as e: 
            logger.logToUser(str(e), level=2, func = inspect.stack()[0][3])

    def closeLinkWidget(self):
        return
        #self.parentWidget.hideLink()
        r'''
        try: 
            # https://stackoverflow.com/questions/5899826/pyqt-how-to-remove-a-widget
            print(self.parentWidget.layout())
            self.parentWidget.layout().removeWidget(self.parentWidget.link)
            print(self.parentWidget.layout())
            self.parentWidget.link_url = "" 
            self.parentWidget.link = None
            return True
        except Exception as e: 
            logger.logToUser(str(e), level=2, func = inspect.stack()[0][3])
            return True 
        '''

