
import PyQt5 
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QPushButton, QPushButton, QLabel, QVBoxLayout, QWidget
from PyQt5 import QtCore
import threading
import time 

def logToUser(msg: str, func=None, level: int = 2, plugin = None):
      print("Log to user")
      dockwidget = plugin
      if dockwidget is None: return
      try: 
            if func is not None:
                  msg += "\n" + str(func)
            if level == 0: msg = "🛈 " + msg
            if level == 1: msg = "⚠️ " + msg
            if level == 2: msg = "❗ " + msg
            dockwidget.showError(msg = msg, level = level)
      except Exception as e: print(e); return 

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
