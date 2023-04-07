
import qgis.PyQt 
from qgis.PyQt.QtWidgets import QMainWindow, QMessageBox, QPushButton, QPushButton, QLabel, QVBoxLayout, QWidget
from qgis.PyQt import QtCore
import threading
import time

from plugin_utils.helpers import splitTextIntoLines 

def logToUser(msg: str, func=None, level: int = 2, plugin = None, url = "", blue = False):
      print("Log to user")
      #time.sleep(0.3)
      #t_name = threading.current_thread().getName()

      msg = str(msg)
      dockwidget = plugin
      try: 
            if url == "" and blue is False: # only for info messages
                  msg = addLevelSymbol(msg, level)
                  if func is not None: 
                        msg += "::" + str(func)
            writeToLog(msg, level)
            
            if dockwidget is None: return

            new_msg = splitTextIntoLines(msg, 70)

            #if url == "" and blue is False:
            #      new_msg = addLevelSymbol(new_msg, level)

            dockwidget.msgLog.sendMessage.emit(new_msg, level, url, blue)
            #dockwidget.msgLog.addButton(new_msg, level=level, blue=blue)
            
      except Exception as e: print(e); return 

def addLevelSymbol(msg: str, level: int):
      if level == 0: msg = "🛈 " + msg
      if level == 1: msg = "⚠️ " + msg
      if level == 2: msg = "❗ " + msg
      return msg 

def writeToLog(msg: str = "", level: int = 2):
      print("write log")
      from speckle.logging import logger
      logger.log(msg, level)
       

def displayUserMsg(msg: str, func=None, level: int = 2): 
      try:
            window = createWindow(msg, func, level)
            window.exec_() 
      except Exception as e: print(e)

def createWindow(msg_old: str, func=None, level: int = 2):
      print("Create window")
      window = None
      try:
            # https://www.techwithtim.net/tutorials/pyqt5-tutorial/messageboxes/
            window = QMessageBox()
            msg = ""
            if len(msg_old)>80:
                  try:
                        for i, x in enumerate(msg_old):
                              msg += x
                              if i!=0 and i%80 == 0: msg += "\n"
                  except Exception as e: print(e)
            else: 
                  msg = msg_old
      
            window.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
            if level==0: 
                  window.setWindowTitle("Info")
                  window.setIcon(QMessageBox.Icon.Information)
            if level==1: 
                  window.setWindowTitle("Warning")
                  window.setIcon(QMessageBox.Icon.Warning)
            elif level==2: 
                  window.setWindowTitle("Error")
                  window.setIcon(QMessageBox.Icon.Critical)
            window.setFixedWidth(200)

            if func is not None:
                  window.setText(str(msg + "\n" + str(func)))
            else: 
                  window.setText(str(msg))
            print(window)
      except Exception as e: print(e)
      return window 

