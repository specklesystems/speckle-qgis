
import threading
import time
from typing import Any, List
from plugin_utils.helpers import splitTextIntoLines
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, pyqtSignal, QTranslator, QRect, QObject
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget, QPushButton
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtGui import QPainter
import webbrowser
from specklepy.logging import metrics
from specklepy.api.credentials import Account

import inspect

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

BACKGR_COLOR = f"background-color: rgb{str(SPECKLE_COLOR)};"
BACKGR_COLOR_LIGHT = f"background-color: rgb{str(SPECKLE_COLOR_LIGHT)};"

BACKGR_COLOR_GREY = f"background-color: Gainsboro;"

class LogWidget(QWidget):
    
    msgs: List[str] = []
    used_btns: List[int] = []
    btns: List[QPushButton]
    max_msg: int
    sendMessage = pyqtSignal(str, int, str, bool)

    active_account: Account
    speckle_version: str
    
    # constructor
    def __init__(self, parent=None):
        super(LogWidget, self).__init__(parent)
        print("start LogWidget")
        self.parentWidget = parent
        print(self.parentWidget)
        self.max_msg = 10
        
        # create a temporary floating button 
        width = 0 #parent.frameSize().width()
        height = 0 # parent.frameSize().height()
        
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgba(250,250,250,80);")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 60, 10, 20)
        self.layout.setAlignment(Qt.AlignBottom) 
        self.setGeometry(0, 0, width, height)

        # generate 100 buttons to use later
        self.btns = []
        for i in range(self.max_msg):
            button = QPushButton(f"👌 Error") # to '{streamName}' Sent , v
            button.setStyleSheet("QPushButton {color: black; border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR_GREY}" + "}")
            button.clicked.connect(lambda: self.openLink())
            button.clicked.connect(lambda: self.hide())
            self.btns.append(button)

        self.hide() 

    # overriding the mouseReleaseEvent method
    def mouseReleaseEvent(self, event):
        print("Mouse Release Event")
        self.hide() 
        #self.parentWidget.hideError()

    def hide(self):
        
        self.setGeometry(0, 0, 0, 0)

        # remove all buttons
        for i in reversed(range(self.layout.count())): 
           self.layout.itemAt(i).widget().setParent(None)

        # remove list of used btns
        self.used_btns.clear()
        self.msgs.clear()

    def addButton(self, text: str = "something went wrong", level: int = 2, url = "", blue = False):
        print("Add button")

        self.setGeometry(0, 0, self.parentWidget.frameSize().width(), self.parentWidget.frameSize().height())
        
        # find index of the first unused button
        btn, index = self.getNextBtn()
        btn.setAccessibleName(url)

        if url != "":
            btn.setStyleSheet("QPushButton {color: white;border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR}" + "} QPushButton:hover { "+ f"{BACKGR_COLOR_LIGHT}" + " }")
        
        else:
            if blue is False: 
                btn.setStyleSheet("QPushButton {color: black; border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR_GREY}" + "}")
            else:
                btn.setStyleSheet("QPushButton {color: white;border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR}" + "}")
        
        
        btn.setText(text)
        self.resizeToText(btn)

        #btn.resize(btn.sizeHint())
        self.layout.addWidget(btn) #, alignment=Qt.AlignCenter) 

        self.msgs.append(text)
        self.used_btns.append(1)

    def openLink(self, url = ""):
        try:
            btn = self.sender()
            url = btn.accessibleName()
            if url == "": return

            webbrowser.open(url, new=0, autoraise=True)
            
            try:
                metrics.track("Connector Action", self.active_account, {"name": "Open In Web", "connector_version": str(self.speckle_version)})
            except:
                pass   
               
            self.hide()
        except Exception as e: 
            pass #logger.logToUser(str(e), level=2, func = inspect.stack()[0][3])

    def getNextBtn(self):
        index = len(self.used_btns) # get the next "free" button 

        if index >= len(self.btns): 
            # remove first button
            self.layout.itemAt(0).widget().setParent(None)

            self.used_btns.clear()
            index = 0 

        btn = self.btns[index]
        return btn, index 

    def resizeToText(self, btn):
        try:
            text = btn.text()
            if len(text.split("\n"))>2:
                height = len(text.split("\n"))*30
                btn.setMinimumHeight(height)
            return btn 
        except Exception as e: 
            print(e)
            return btn 