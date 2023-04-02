# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpeckleQGISDialog
                                 A QGIS plugin
 SpeckleQGIS Description
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-08-04
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Speckle Systems
        email                : alan@speckle.systems
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import inspect
import os
import threading
from plugin_utils.helpers import splitTextIntoLines
from speckle.converter.layers import getLayers
from speckle.DataStorage import DataStorage
from speckle.notifications.UpdatesLogger import UpdatesLogger
from ui.LogWidget import LogWidget
from ui.logger import logToUser
#from speckle_qgis import SpeckleQGIS
import ui.speckle_qgis_dialog
from qgis.core import Qgis, QgsProject,QgsVectorLayer, QgsRasterLayer, QgsIconUtils 
from specklepy.logging.exceptions import (SpeckleException, GraphQLException)
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt import QtGui
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import QCheckBox, QListWidgetItem, QAction, QDockWidget, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import pyqtSignal, Qt 
from speckle.logging import logger
from specklepy.api.credentials import get_local_accounts

from specklepy.api.wrapper import StreamWrapper
from specklepy.api.client import SpeckleClient
from specklepy.logging import metrics

from ui.validation import tryGetBranch, tryGetStream

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "speckle_qgis_dialog_base.ui")
)

COLOR_HIGHLIGHT = (210,210,210)

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)
ICON_LOGO = os.path.dirname(os.path.abspath(__file__)) + "/logo-slab-white@0.5x.png"

ICON_SEARCH = os.path.dirname(os.path.abspath(__file__)) + "/magnify.png"

ICON_DELETE = os.path.dirname(os.path.abspath(__file__)) + "/delete.png"
ICON_DELETE_BLUE = os.path.dirname(os.path.abspath(__file__)) + "/delete-blue.png"

ICON_SEND = os.path.dirname(os.path.abspath(__file__)) + "/cube-send.png"
ICON_RECEIVE = os.path.dirname(os.path.abspath(__file__)) + "/cube-receive.png"

ICON_SEND_BLACK = os.path.dirname(os.path.abspath(__file__)) + "/cube-send-black.png"
ICON_RECEIVE_BLACK = os.path.dirname(os.path.abspath(__file__)) + "/cube-receive-black.png"

ICON_SEND_BLUE = os.path.dirname(os.path.abspath(__file__)) + "/cube-send-blue.png"
ICON_RECEIVE_BLUE = os.path.dirname(os.path.abspath(__file__)) + "/cube-receive-blue.png"

COLOR = f"color: rgb{str(SPECKLE_COLOR)};"
BACKGR_COLOR = f"background-color: rgb{str(SPECKLE_COLOR)};"
BACKGR_COLOR_LIGHT = f"background-color: rgb{str(SPECKLE_COLOR_LIGHT)};"

class SpeckleQGISDialog(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    streamList: QtWidgets.QComboBox
    sendModeButton: QtWidgets.QPushButton
    receiveModeButton: QtWidgets.QPushButton
    streamBranchDropdown: QtWidgets.QComboBox
    layerSendModeDropdown: QtWidgets.QComboBox
    commitDropdown: QtWidgets.QComboBox
    layersWidget: QtWidgets.QListWidget
    saveLayerSelection: QtWidgets.QPushButton
    runButton: QtWidgets.QPushButton
    experimental: QCheckBox
    msgLog: LogWidget = None
    updLog: UpdatesLogger = None
    dataStorage: DataStorage = None
    
    def __init__(self, parent=None):
        """Constructor."""
        super(SpeckleQGISDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.streamBranchDropdown.setMaxCount(100)
        self.commitDropdown.setMaxCount(100)

        self.streams_add_button.setFlat(True)
        self.streams_remove_button.setFlat(True)
        self.saveSurveyPoint.setFlat(True)
        self.saveLayerSelection.setFlat(True)
        self.reloadButton.setFlat(True)
        self.closeButton.setFlat(True)

        # https://stackoverflow.com/questions/67585501/pyqt-how-to-use-hover-in-button-stylesheet
        #color = f"color: rgb{str(SPECKLE_COLOR)};"
        #backgr_color = f"background-color: rgb{str(SPECKLE_COLOR)};"
        #backgr_color_light = f"background-color: rgb{str(SPECKLE_COLOR_LIGHT)};"
        backgr_image_del = f"border-image: url({ICON_DELETE_BLUE});"
        self.streams_add_button.setIcon(QIcon(ICON_SEARCH))
        self.streams_add_button.setMaximumWidth(25)
        self.streams_add_button.setStyleSheet("QPushButton {padding:3px;padding-left:5px;border: none; text-align: left;} QPushButton:hover { " + f"background-color: rgb{str(COLOR_HIGHLIGHT)};" + f"{COLOR}" + " }")
        self.streams_remove_button.setIcon(QIcon(ICON_DELETE))
        self.streams_remove_button.setMaximumWidth(25)
        self.streams_remove_button.setStyleSheet("QPushButton {padding:3px;padding-left:5px;border: none; text-align: left; image-position:right} QPushButton:hover { " + f"background-color: rgb{str(COLOR_HIGHLIGHT)};" + f"{COLOR}" + " }") #+ f"{backgr_image_del}" 

        self.saveLayerSelection.setStyleSheet("QPushButton {text-align: right;} QPushButton:hover { " + f"{COLOR}" + " }")
        self.saveSurveyPoint.setStyleSheet("QPushButton {text-align: right;} QPushButton:hover { " + f"{COLOR}" + " }")
        self.reloadButton.setStyleSheet("QPushButton {text-align: left;} QPushButton:hover { " + f"{COLOR}" + " }")
        self.closeButton.setStyleSheet("QPushButton {text-align: right;} QPushButton:hover { " + f"{COLOR}" + " }")


        self.sendModeButton.setStyleSheet("QPushButton {padding: 10px; border: 0px; " + f"color: rgb{str(SPECKLE_COLOR)};"+ "} QPushButton:hover { "  + "}" ) 
        self.sendModeButton.setIcon(QIcon(ICON_SEND_BLUE))
        
        self.receiveModeButton.setFlat(True)
        self.receiveModeButton.setStyleSheet("QPushButton {padding: 10px; border: 0px;}"+ "QPushButton:hover { "  + f"background-color: rgb{str(COLOR_HIGHLIGHT)};" + "}" ) 
        self.receiveModeButton.setIcon(QIcon(ICON_RECEIVE_BLACK))

        self.runButton.setStyleSheet("QPushButton {color: white;border: 0px;border-radius: 17px;padding: 10px;"+ f"{BACKGR_COLOR}" + "} QPushButton:hover { "+ f"{BACKGR_COLOR_LIGHT}" + " }")
        #self.runButton.setGeometry(0, 0, 150, 30)
        self.runButton.setMaximumWidth(200)
        self.runButton.setIcon(QIcon(ICON_SEND))

        # insert checkbox 
        l = self.verticalLayout
        #l_item = None
        
        #for i in reversed(range(self.verticalLayout.count())): 
        #   l_item = self.verticalLayout.itemAt(i).widget()

        # add row with "experimental" checkbox 
        box = QWidget()
        box.layout = QHBoxLayout(box)
        btn = QtWidgets.QCheckBox("Send/receive in the background (experimental!)")
        btn.setStyleSheet("QPushButton {color: black; border: 0px;padding: 0px;height: 40px;text-align: left;}")
        box.layout.addWidget(btn)
        box.layout.setContentsMargins(65, 0, 0, 0)
        self.formLayout.insertRow(10,box)
        self.experimental = btn

        # add widgets that will only show on event trigger 
        logWidget = LogWidget(parent=self)
        self.layout().addWidget(logWidget)
        self.msgLog = logWidget 

    
    def addProps(self, plugin):
        self.dataStorage = plugin.dataStorage
        
        # add notification trigger widget 
        updateWidget = UpdatesLogger(parent=self)
        #self.layout().addWidget(logWidget)
        self.updLog = updateWidget 

        self.msgLog.active_account = plugin.active_account
        self.msgLog.speckle_version = plugin.version

    def addLabel(self, plugin): 
        try:
            exitIcon = QPixmap(ICON_LOGO)
            #scaledExitIcon = exitIcon.scaled(QtCore.QSize(100, 31))
            exitActIcon = QIcon(exitIcon)

            # create a label 
            text_label = QtWidgets.QPushButton(" for QGIS")
            text_label.setStyleSheet("border: 0px;"
                                "color: white;"
                                f"{BACKGR_COLOR}"
                                "top-margin: 40 px;"
                                "padding: 10px;"
                                "padding-left: 20px;"
                                "font-size: 15px;"
                                "height: 30px;"
                                "text-align: left;"
                                )
            text_label.setIcon(exitActIcon)
            text_label.setIconSize(QtCore.QSize(300, 93))
            text_label.setMinimumSize(QtCore.QSize(100, 40))
            text_label.setMaximumWidth(200)

            version = ""
            try: 
                if isinstance(plugin.version, str): version = str(plugin.version)
            except: pass


            version_label = QtWidgets.QPushButton(version)
            version_label.setStyleSheet("border: 0px;"
                                "color: white;"
                                f"{BACKGR_COLOR}"
                                "padding-top: 15px;"
                                "padding-left: 0px;"
                                "margin-left: 0px;"
                                "font-size: 10px;"
                                "height: 30px;"
                                "text-align: left;"
                                )

            widget = QWidget()
            widget.setStyleSheet(f"{BACKGR_COLOR}")
            connect_box = QHBoxLayout(widget)
            connect_box.addWidget(text_label) #, alignment=Qt.AlignCenter) 
            connect_box.addWidget(version_label) 
            connect_box.setContentsMargins(0, 0, 0, 0)
            self.setTitleBarWidget(widget)
        except Exception as e:
            logToUser(e)

    def resizeEvent(self, event):
        try:
            #print("resize")
            QtWidgets.QDockWidget.resizeEvent(self, event)
            if self.msgLog.size().height() != 0: # visible
                self.msgLog.setGeometry(0, 0, self.msgLog.parentWidget.frameSize().width(), self.msgLog.parentWidget.frameSize().height()) #.resize(self.frameSize().width(), self.frameSize().height())
        except Exception as e:
            #logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def clearDropdown(self):
        try:
            #self.streamIdField.clear()
            self.streamBranchDropdown.clear()
            self.commitDropdown.clear()
            #self.layerSendModeDropdown.clear()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def reloadDialogUI(self, plugin):
        try:

            #logToUser("long errror something something msg1", level=2, plugin= plugin)

            self.clearDropdown()
            self.populateUI(plugin) 
            self.enableElements(plugin)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    
    def run(self, plugin): 
        try:
            # Setup events on first load only!
            self.setupOnFirstLoad(plugin)
            # Connect streams section events
            self.completeStreamSection(plugin)
            # Populate the UI dropdowns
            self.populateUI(plugin) 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def closeEvent(self, event):
        try:
            self.closingPlugin.emit()
            event.accept()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return
        
    def addMsg(self, text:str, level:int, url:str, blue:bool):
        #t_name = threading.current_thread().getName()
        #print(t_name)
        self.msgLog.addButton(text, level, url, blue)
    
    def addUpdate(self, branch_name: str, latest_commit_id: str):
        #t_name = threading.current_thread().getName()
        #print(t_name)
        self.msgLog.addButton(f"Branch \"{branch_name}\" was updated", 0, "", True)
        for i, tup in enumerate(self.dataStorage.streamsToFollow):
            (url, uuid, commit_id) = tup
            url = url.split(" ")[0].split("?")[0].split("&")[0]
            branch = tryGetBranch(url)
            if branch_name == branch.name:
                self.dataStorage.streamsToFollow[i] = (url, uuid, latest_commit_id)
        return

    def setupOnFirstLoad(self, plugin):
        try:
            self.runButton.clicked.connect(plugin.onRunButtonClicked)

            self.msgLog.sendMessage.connect(self.addMsg)
            self.updLog.sendUpdate.connect(self.addUpdate)

            self.streams_add_button.clicked.connect( plugin.onStreamAddButtonClicked )
            self.reloadButton.clicked.connect(lambda: self.refreshClicked(plugin))
            self.closeButton.clicked.connect(lambda: self.closeClicked(plugin))
            self.saveSurveyPoint.clicked.connect(plugin.set_survey_point)
            self.saveLayerSelection.clicked.connect(lambda: self.populateLayerDropdown(plugin))
            self.sendModeButton.clicked.connect(lambda: self.setSendMode(plugin))
            self.layerSendModeDropdown.currentIndexChanged.connect( lambda: self.layerSendModeChange(plugin) )
            self.receiveModeButton.clicked.connect(lambda: self.setReceiveMode(plugin))

            self.streamBranchDropdown.currentIndexChanged.connect( lambda: self.runBtnStatusChanged(plugin) )
            self.commitDropdown.currentIndexChanged.connect( lambda: self.runBtnStatusChanged(plugin) )

            self.closingPlugin.connect(plugin.onClosePlugin)
            return 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def refreshClicked(self, plugin):
        try:
            try:
                metrics.track("Connector Action", plugin.active_account, {"name": "Refresh", "connector_version": str(plugin.version)})
            except Exception as e:
                logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget )
            
            plugin.reloadUI()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def closeClicked(self, plugin):
        try:
            try:
                metrics.track("Connector Action", plugin.active_account, {"name": "Close", "connector_version": str(plugin.version)})
            except Exception as e:
                logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget )
            
            plugin.onClosePlugin()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def setSendMode(self, plugin):
        try:
            plugin.btnAction = 0 # send 
            color = f"color: rgb{str(SPECKLE_COLOR)};"
            self.sendModeButton.setStyleSheet("border: 0px;"
                                        f"color: rgb{str(SPECKLE_COLOR)};"
                                        "padding: 10px;")
            self.sendModeButton.setIcon(QIcon(ICON_SEND_BLUE))
            self.sendModeButton.setFlat(False)
            self.receiveModeButton.setFlat(True)
            self.receiveModeButton.setStyleSheet("QPushButton {border: 0px; color: black; padding: 10px; } QPushButton:hover { " + f"background-color: rgb{str(COLOR_HIGHLIGHT)};" +  " };")
            self.receiveModeButton.setIcon(QIcon(ICON_RECEIVE_BLACK))
            #self.receiveModeButton.setFlat(True)
            self.runButton.setProperty("text", " SEND")
            self.runButton.setIcon(QIcon(ICON_SEND))

            # enable sections only if in "saved streams" mode 
            if self.layerSendModeDropdown.currentIndex() == 1: self.layersWidget.setEnabled(True)
            if self.layerSendModeDropdown.currentIndex() == 1: self.saveLayerSelection.setEnabled(True)
            self.commitDropdown.setEnabled(False)
            self.messageInput.setEnabled(True)
            self.layerSendModeDropdown.setEnabled(True)

            self.runBtnStatusChanged(plugin)
            return
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return
    
    def setReceiveMode(self, plugin):
        try:
            plugin.btnAction = 1 # receive 
            color = f"color: rgb{str(SPECKLE_COLOR)};"
            self.receiveModeButton.setStyleSheet("border: 0px;"
                                        f"color: rgb{str(SPECKLE_COLOR)};"
                                        "padding: 10px;")
            self.sendModeButton.setIcon(QIcon(ICON_SEND_BLACK))
            self.sendModeButton.setStyleSheet("QPushButton {border: 0px; color: black; padding: 10px;} QPushButton:hover { " + f"background-color: rgb{str(COLOR_HIGHLIGHT)};"  + " };")
            self.receiveModeButton.setIcon(QIcon(ICON_RECEIVE_BLUE))
            self.sendModeButton.setFlat(True)
            self.receiveModeButton.setFlat(False)
            #self.sendModeButton.setFlat(True)
            self.runButton.setProperty("text", " RECEIVE")
            self.runButton.setIcon(QIcon(ICON_RECEIVE))
            #self.layerSendModeChange(plugin, 1)
            self.commitDropdown.setEnabled(True)
            self.layersWidget.setEnabled(False)
            self.messageInput.setEnabled(False)
            self.saveLayerSelection.setEnabled(False)
            self.layerSendModeDropdown.setEnabled(False)

            self.runBtnStatusChanged(plugin)
            return
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def completeStreamSection(self, plugin):
        try:
            self.streams_remove_button.clicked.connect( lambda: self.onStreamRemoveButtonClicked(plugin) )
            self.streamList.currentIndexChanged.connect( lambda: self.onActiveStreamChanged(plugin) )
            self.streamBranchDropdown.currentIndexChanged.connect( lambda: self.populateActiveCommitDropdown(plugin) )
            return
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def populateUI(self, plugin):
        try:
            self.populateLayerSendModeDropdown()
            self.populateLayerDropdown(plugin, False)
            #items = [self.layersWidget.item(x).text() for x in range(self.layersWidget.count())]
            self.populateProjectStreams(plugin)
            self.populateSurveyPoint(plugin)

            self.runBtnStatusChanged(plugin)
            self.runButton.setEnabled(False) 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return
    
    def runBtnStatusChanged(self, plugin):
        try:
            commitStr = str(self.commitDropdown.currentText())
            branchStr = str(self.streamBranchDropdown.currentText())

            if plugin.btnAction == 1: # on receive
                if commitStr == "": 
                    self.runButton.setEnabled(False) 
                else: 
                    self.runButton.setEnabled(True) 
            
            if plugin.btnAction == 0: # on send 
                if branchStr == "": 
                    self.runButton.setEnabled(False) 
                elif branchStr != "" and self.layerSendModeDropdown.currentIndex() == 1 and len(plugin.current_layers) == 0: # saved layers; but the list is empty 
                    self.runButton.setEnabled(False)
                else:
                    self.runButton.setEnabled(True)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return
            

    def layerSendModeChange(self, plugin, runMode = None):
        try:
            if self.layerSendModeDropdown.currentIndex() == 0 or runMode == 1: # by manual selection OR receive mode
                self.current_layers = []
                self.layersWidget.setEnabled(False)
                self.saveLayerSelection.setEnabled(False)
                
            elif self.layerSendModeDropdown.currentIndex() == 1 and (runMode == 0 or runMode is None): # by saved AND when Send mode
                self.layersWidget.setEnabled(True)
                self.saveLayerSelection.setEnabled(True)
            
            branchStr = str(self.streamBranchDropdown.currentText())
            if self.layerSendModeDropdown.currentIndex() == 0:
                if branchStr == "": self.runButton.setEnabled(False) # by manual selection
                else: self.runButton.setEnabled(True) # by manual selection
            elif self.layerSendModeDropdown.currentIndex() == 1: self.runBtnStatusChanged(plugin) # by saved

        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def populateLayerDropdown(self, plugin, bySelection: bool = True):
        
        try:
            if not self: return
            from ui.project_vars import set_project_layer_selection
            
            self.layersWidget.clear()
            nameDisplay = [] 
            project = plugin.qgis_project

            if bySelection is False: # read from project data 

                all_layers_ids = [l.id() for l in project.mapLayers().values()]
                for layer_tuple in plugin.current_layers:
                    if layer_tuple[1].id() in all_layers_ids: 
                        listItem = self.fillLayerList(layer_tuple[1]) 
                        self.layersWidget.addItem(listItem)

            else: # read selected layers 
                # Fetch selected layers

                plugin.current_layers = []
                layers = getLayers(plugin, bySelection) # List[QgsLayerTreeNode]
                for i, layer in enumerate(layers):
                    plugin.current_layers.append((layer.name(), layer)) 
                    listItem = self.fillLayerList(layer)
                    self.layersWidget.addItem(listItem)

                set_project_layer_selection(plugin)

            self.layersWidget.setIconSize(QtCore.QSize(20, 20))
            self.runBtnStatusChanged(plugin)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def fillLayerList(self, layer):
        try:
            icon_xxl = os.path.dirname(os.path.abspath(__file__)) + "/size-xxl.png"
            listItem = QListWidgetItem(layer.name()) 

            if isinstance(layer, QgsRasterLayer) and layer.width()*layer.height() > 1000000:
                    listItem.setIcon(QIcon(icon_xxl))
            
            elif isinstance(layer, QgsVectorLayer) and layer.featureCount() > 20000:
                    listItem.setIcon(QIcon(icon_xxl))

            else: 
                icon = QgsIconUtils().iconForLayer(layer)
                listItem.setIcon(icon)
            
            return listItem
        
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return


    def populateSurveyPoint(self, plugin):
        if not self:
            return
        try:
            self.surveyPointLat.clear()
            self.surveyPointLat.setText(str(plugin.lat))
            self.surveyPointLon.clear()
            self.surveyPointLon.setText(str(plugin.lon))
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def enableElements(self, plugin):
        try:
            self.sendModeButton.setEnabled(plugin.is_setup)
            self.receiveModeButton.setEnabled(plugin.is_setup)
            self.runButton.setEnabled(plugin.is_setup)
            self.streams_add_button.setEnabled(plugin.is_setup)
            if plugin.is_setup is False: self.streams_remove_button.setEnabled(plugin.is_setup) 
            self.streamBranchDropdown.setEnabled(plugin.is_setup)
            self.layerSendModeDropdown.setEnabled(plugin.is_setup)
            self.commitDropdown.setEnabled(False)
            self.show()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def populateProjectStreams(self, plugin):
        try:
            from ui.project_vars import set_project_streams
            if not self: return
            self.streamList.clear()
            for stream in plugin.current_streams: 
                self.streamList.addItems(
                [f"Stream not accessible - {stream[0].stream_id}" if stream[1] is None or isinstance(stream[1], SpeckleException) else f"{stream[1].name}, {stream[1].id} | {stream[0].stream_url.split('/streams')[0]}"] 
            )
            if len(plugin.current_streams)==0: self.streamList.addItems([""])
            self.streamList.addItems(["Create New Stream"])
            set_project_streams(plugin)
            index = self.streamList.currentIndex()
            if index == -1: self.streams_remove_button.setEnabled(False)
            else: self.streams_remove_button.setEnabled(True)

            if len(plugin.current_streams)>0: plugin.active_stream = plugin.current_streams[0]
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def onActiveStreamChanged(self, plugin):
        try:
            if not self: return
            index = self.streamList.currentIndex()
            if (len(plugin.current_streams) == 0 and index ==1) or (len(plugin.current_streams)>0 and index == len(plugin.current_streams)): 
                self.populateProjectStreams(plugin)
                plugin.onStreamCreateClicked()
                return
            if len(plugin.current_streams) == 0: return
            if index == -1: return

            try: plugin.active_stream = plugin.current_streams[index]
            except: plugin.active_stream = None

            self.populateActiveStreamBranchDropdown(plugin)
            self.populateActiveCommitDropdown(plugin)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return
        
    def populateLayerSendModeDropdown(self):
        if not self: return
        try:
            self.layerSendModeDropdown.clear()
            self.layerSendModeDropdown.addItems(
                ["Send selected layers", "Send saved layers"]
            )
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def populateActiveStreamBranchDropdown(self, plugin):
        if not self: return
        try:
            if plugin.active_stream is None: return
            self.streamBranchDropdown.clear()
            if isinstance(plugin.active_stream[1], SpeckleException): 
                logToUser("Some streams cannot be accessed", level = 1, plugin = self)
                return
            elif plugin.active_stream is None or plugin.active_stream[1] is None or plugin.active_stream[1].branches is None:
                return
            self.streamBranchDropdown.addItems(
                [f"{branch.name}" for branch in plugin.active_stream[1].branches.items]
            )
            self.streamBranchDropdown.addItems(["Create New Branch"])
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

    def populateActiveCommitDropdown(self, plugin):
        if not self: return
        try:
            self.commitDropdown.clear()
            if plugin.active_stream is None: return
            branchName = self.streamBranchDropdown.currentText()
            if branchName == "": return
            if branchName == "Create New Branch": 
                self.streamBranchDropdown.setCurrentText("main")
                plugin.onBranchCreateClicked()
                return
            branch = None
            if isinstance(plugin.active_stream[1], SpeckleException): 
                logToUser("Some streams cannot be accessed", level = 1, plugin = self)
                return
            elif plugin.active_stream[1]:
                for b in plugin.active_stream[1].branches.items:
                    if b.name == branchName:
                        branch = b
                        break
            print(branch)
            self.commitDropdown.addItems(
                [f"{commit.id}"+ " | " + f"{commit.message}" for commit in branch.commits.items]
            )
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            print(str(e) + "::" + str(inspect.stack()[0][3]))
            return

    def onStreamRemoveButtonClicked(self, plugin):
        try:
            from ui.project_vars import set_project_streams
            if not self: return
            index = self.streamList.currentIndex()
            if len(plugin.current_streams) > 0: plugin.current_streams.pop(index)
            plugin.active_stream = None
            self.streamBranchDropdown.clear()
            self.commitDropdown.clear()
            #self.streamIdField.setText("")

            set_project_streams(plugin)
            self.populateProjectStreams(plugin)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self)
            return

