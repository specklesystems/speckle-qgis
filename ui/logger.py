
from PyQt5.QtWidgets import QMessageBox, QPushButton
from PyQt5 import QtCore

import inspect 

def logToUser(msg: str, func=None, level: int = 2):
      print("Log to user")
      window = createWindow(msg, func, level)
      print(window)
      window.exec_() 
      return

def logToUserWithAction(msg: str, func=None, level: int = 2, action_text="Click", callback=None):
      print("Log to user with action")
      window = createWindow(msg, func, level)
      
      window.exec_() 
      return 
      
      if callback is not None:
            button = QPushButton(window)
            button.setText(action_text)
            button.pressed.connect(callback)
            window.layout().addWidget(button)
      window.exec_() 
      return

def createWindow(msg: str, func=None, level: int = 2):
      print("Create window")
      # https://www.techwithtim.net/tutorials/pyqt5-tutorial/messageboxes/
      window = QMessageBox()
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
      return window 