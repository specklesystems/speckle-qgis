
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, QTranslator, QRect, QObject
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget
from qgis.PyQt import QtWidgets

import inspect

from ui.logger import logToUser 

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

class WaitScreenWidget(QWidget):
    # constructor
    def __init__(self, parent=None):
        super(WaitScreenWidget, self).__init__(parent)
        print("start Wait screen widget")
        self.parentWidget = parent
        self.link_btn = None
        width = parent.frameSize().width()
        height = parent.frameSize().height()
        color = f"background-color: rgba(200,200,200,60);"
        
        #self.setStyleSheet("QWidget {" + f"{color}" + ";} QWidget:hover { " + f"{color}" + " }")
        self.setGeometry(0, 0, 0, 0) # 
        
        connect_box = QVBoxLayout(self)
        commit_link_btn = QtWidgets.QPushButton()
        commit_link_btn.setStyleSheet("QPushButton {color: white;border: 0px;padding: 10px;height:"+ str(height+500) +"px;"+ f"{color}" + "} QPushButton:hover { "+ f"{color}" + " }")

        connect_box.addWidget(commit_link_btn) #, alignment=Qt.AlignCenter) 
        connect_box.setContentsMargins(0, 0, 0, 0)
        connect_box.setAlignment(Qt.AlignBottom)  

    def closeWaitWidget(self):
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
            logToUser(str(e), level=2, func = inspect.stack()[0][3])
            return True 
        '''

