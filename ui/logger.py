
from PyQt5.QtWidgets import QMessageBox, QPushButton
from PyQt5 import QtCore

def logToUser(msg: str, func=None, level: int = 2):
      print("Log to user")
      window = createWindow(msg, func, level)
      print(window)
      window.exec_() 
      return

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
            if len(msg_old)>60:
                  try:
                        for i, x in enumerate(msg_old):
                              print(x)
                              msg += x
                              if i!=0 and i%60 == 0: msg += "\n"
                              print(msg)
                  except Exception as e: print(e)
            else: 
                  msg = msg_old

            print(msg)
      
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