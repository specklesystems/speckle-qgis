# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/alan/Documents/Speckle/speckle-qgis/ui/speckle_qgis_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SpeckleQGISDialogBase(object):
    def setupUi(self, SpeckleQGISDialogBase):
        SpeckleQGISDialogBase.setObjectName("SpeckleQGISDialogBase")
        SpeckleQGISDialogBase.resize(575, 651)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setContentsMargins(10, 10, 10, 10)
        self.formLayout.setObjectName("formLayout")
        self.streamListLabel = QtWidgets.QLabel(self.dockWidgetContents)
        self.streamListLabel.setObjectName("streamListLabel")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.streamListLabel)
        self.streamList = QtWidgets.QListWidget(self.dockWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.streamList.sizePolicy().hasHeightForWidth())
        self.streamList.setSizePolicy(sizePolicy)
        self.streamList.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.streamList.setResizeMode(QtWidgets.QListView.Fixed)
        self.streamList.setViewMode(QtWidgets.QListView.ListMode)
        self.streamList.setObjectName("streamList")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.streamList)
        self.streamListButtons = QtWidgets.QHBoxLayout()
        self.streamListButtons.setObjectName("streamListButtons")
        self.streams_add_button = QtWidgets.QPushButton(self.dockWidgetContents)
        self.streams_add_button.setObjectName("streams_add_button")
        self.streamListButtons.addWidget(self.streams_add_button)
        self.streams_remove_button = QtWidgets.QPushButton(self.dockWidgetContents)
        self.streams_remove_button.setObjectName("streams_remove_button")
        self.streamListButtons.addWidget(self.streams_remove_button)
        spacerItem = QtWidgets.QSpacerItem(40, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.streamListButtons.addItem(spacerItem)
        self.formLayout.setLayout(1, QtWidgets.QFormLayout.FieldRole, self.streamListButtons)
        self.streamIdLabel = QtWidgets.QLabel(self.dockWidgetContents)
        self.streamIdLabel.setObjectName("streamIdLabel")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.streamIdLabel)
        self.streamIdField = QtWidgets.QLineEdit(self.dockWidgetContents)
        self.streamIdField.setEnabled(False)
        self.streamIdField.setClearButtonEnabled(False)
        self.streamIdField.setObjectName("streamIdField")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.streamIdField)
        self.streamBranchLabel = QtWidgets.QLabel(self.dockWidgetContents)
        self.streamBranchLabel.setObjectName("streamBranchLabel")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.streamBranchLabel)
        self.streamBranchDropdown = QtWidgets.QComboBox(self.dockWidgetContents)
        self.streamBranchDropdown.setObjectName("streamBranchDropdown")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.streamBranchDropdown)
        self.layersLabel = QtWidgets.QLabel(self.dockWidgetContents)
        self.layersLabel.setObjectName("layersLabel")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.layersLabel)
        self.layersWidget = QtWidgets.QListWidget(self.dockWidgetContents)
        self.layersWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.layersWidget.setObjectName("layersWidget")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.layersWidget)
        self.messageLabel = QtWidgets.QLabel(self.dockWidgetContents)
        self.messageLabel.setObjectName("messageLabel")
        self.formLayout.setWidget(6, QtWidgets.QFormLayout.LabelRole, self.messageLabel)
        self.messageInput = QtWidgets.QLineEdit(self.dockWidgetContents)
        self.messageInput.setObjectName("messageInput")
        self.formLayout.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.messageInput)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.reloadButton = QtWidgets.QPushButton(self.dockWidgetContents)
        self.reloadButton.setEnabled(True)
        self.reloadButton.setObjectName("reloadButton")
        self.horizontalLayout.addWidget(self.reloadButton)
        self.receiveButton = QtWidgets.QPushButton(self.dockWidgetContents)
        self.receiveButton.setEnabled(True)
        self.receiveButton.setObjectName("receiveButton")
        self.horizontalLayout.addWidget(self.receiveButton)
        self.sendButton = QtWidgets.QPushButton(self.dockWidgetContents)
        self.sendButton.setObjectName("sendButton")
        self.horizontalLayout.addWidget(self.sendButton)
        self.formLayout.setLayout(7, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout)
        self.verticalLayout.addLayout(self.formLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        SpeckleQGISDialogBase.setWidget(self.dockWidgetContents)

        self.retranslateUi(SpeckleQGISDialogBase)
        QtCore.QMetaObject.connectSlotsByName(SpeckleQGISDialogBase)

    def retranslateUi(self, SpeckleQGISDialogBase):
        _translate = QtCore.QCoreApplication.translate
        SpeckleQGISDialogBase.setWindowTitle(_translate("SpeckleQGISDialogBase", "SpeckleQGIS"))
        self.streamListLabel.setText(_translate("SpeckleQGISDialogBase", "Project Streams"))
        self.streams_add_button.setText(_translate("SpeckleQGISDialogBase", "+"))
        self.streams_remove_button.setText(_translate("SpeckleQGISDialogBase", "-"))
        self.streamIdLabel.setText(_translate("SpeckleQGISDialogBase", "Active Stream"))
        self.streamBranchLabel.setText(_translate("SpeckleQGISDialogBase", "Branch"))
        self.layersLabel.setText(_translate("SpeckleQGISDialogBase", "Layer"))
        self.messageLabel.setText(_translate("SpeckleQGISDialogBase", "Message"))
        self.messageInput.setPlaceholderText(_translate("SpeckleQGISDialogBase", "Sent XXX objects from QGIS"))
        self.reloadButton.setText(_translate("SpeckleQGISDialogBase", "Reload"))
        self.receiveButton.setText(_translate("SpeckleQGISDialogBase", "Receive"))
        self.sendButton.setText(_translate("SpeckleQGISDialogBase", "Send"))
