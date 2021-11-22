import os
from qgis.PyQt import QtWidgets, uic, QtGui, QtCore


class AddStreamModalDialog(QtWidgets.QDialog):
    def __init__(self):
        super(AddStreamModalDialog,self).__init__(None,QtCore.Qt.WindowStaysOnTopHint)