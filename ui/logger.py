
import PyQt5 
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QPushButton, QPushButton, QLabel, QVBoxLayout, QWidget
from PyQt5 import QtCore
import threading
import time

from plugin_utils.helpers import splitTextIntoLines 

def logToUser(msg: str, func=None, level: int = 2, plugin = None, blue = False):
      print("Log to user")
      time.sleep(0.3)

      msg = str(msg)
      dockwidget = plugin
      try: 
            if func is not None: msg += "::" + str(func)
            print(msg)
            writeToLog(msg, level)
            return
            if dockwidget is None: return

            new_msg = splitTextIntoLines(msg, 70)

            if blue is True: 
                  dockwidget.msgLog.addInfoButton(new_msg, level=level)
            else:
                  new_msg = addLevelSymbol(new_msg, level)
                  dockwidget.msgLog.addButton(new_msg, level=level)
            
      except Exception as e: print(e); return 

def logToUserWithAction(msg: str, level: int = 0, plugin = None, url = ""):
      print("Log to user with action")
      time.sleep(0.3)
      
      msg = str(msg)
      dockwidget = plugin
      if dockwidget is None: return
      try:             
            new_msg = splitTextIntoLines(msg, 70)
            dockwidget.msgLog.addLinkButton(new_msg, level=level, url=url)
            writeToLog(new_msg, level)
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
       
r'''
def displayUserMsg(msg: str, func=None, level: int = 2): 
      try:
            window = createWindow(msg, func, level)
            window.exec_() 
      except Exception as e: print(e)

def logToUserWithAction(msg: str, func=None, level: int = 2, action_text="Click", callback=None):
      print("Log to user with action")
      window = createWindow(msg, func, level)
      
      if window is not None: 
            window.exec_() 
      return 
      
      if callback is not None:
            button = QPushButton(window)
            button.setText(action_text)
            button.pressed.connect(callback)
            window.layout().addWidget(button)
      window.exec_() 
      return

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
'''
