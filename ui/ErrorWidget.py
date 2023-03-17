
from typing import List
from plugin_utils.helpers import splitTextIntoLines
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, QTranslator, QRect, QObject
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget, QPushButton
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtGui import QPainter
import webbrowser

import inspect

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

class ErrorWidget(QWidget):
    
    errors: List[str] = []
    used_btns: List[int] = []
    btns: List[QPushButton]

    # constructor
    def __init__(self, parent=None):
        super(ErrorWidget, self).__init__(parent)
        print("start ErrorWidget")
        self.parentWidget = parent
        print(self.parentWidget)
        
        # create a temporary floating button 
        width = 0 #parent.frameSize().width()
        height = 0 # parent.frameSize().height()
        backgr_color = f"background-color: lightgrey;"
        backgr_color_light = f"background-color: lightgrey;"
        
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgba(200,200,200,70);")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 60, 0, 20)
        self.layout.setAlignment(Qt.AlignBottom) 
        self.setGeometry(0, 0, width, height)

        # generate 100 buttons to use later
        self.btns = []
        for i in range(10):
            button = QPushButton(f"👌 Error") # to '{streamName}' Sent , v
            button.setStyleSheet("QPushButton {color: black; border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{backgr_color}" + "} QPushButton:hover { "+ f"{backgr_color_light}" + " }")
            button.clicked.connect(lambda: self.hide())
            self.btns.append(button)

        self.hide() 

    def drawBackground(self, qp):
        func, kwargs = self.func
        if func is not None:
            kwargs["qp"] = qp
            func(**kwargs)

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
        self.errors.clear()


    def addButton(self, text: str = "something went wrong", level: int = 2):

        # find index of the first unused button
        index = len(self.used_btns)
        if index >= len(self.btns): 
            self.used_btns.clear()
            index = 0 
        btn = self.btns[index] # get the next "free" button 
        
        btn.setText(text)
        if len(text)>153:
            btn.resize(btn.size().width(), 60)

        #btn.resize(btn.sizeHint())
        self.layout.addWidget(btn) #, alignment=Qt.AlignCenter) 

        self.errors.append(text)
        self.used_btns.append(1)
