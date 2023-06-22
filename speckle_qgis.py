# -*- coding: utf-8 -*-

import inspect
import os.path
import sys
import time 
from typing import Any, Callable, List, Optional, Tuple, Union

from datetime import datetime

import threading
from plugin_utils.helpers import getAppName, removeSpecialCharacters
from qgis.core import (Qgis, QgsProject, QgsLayerTreeLayer,
                       QgsLayerTreeGroup, QgsCoordinateReferenceSystem,
                       QgsRasterLayer, QgsVectorLayer,
                       QgsUnitTypes)
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, QTranslator, QRect 
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QApplication, QAction, QDockWidget, QVBoxLayout, QWidget
from qgis.PyQt import QtWidgets
from qgis import PyQt

import sip

from specklepy.core.api import operations
from specklepy.logging.exceptions import SpeckleException, GraphQLException
from specklepy.api.models import Stream
from specklepy.api.wrapper import StreamWrapper
from specklepy.objects import Base
from specklepy.objects.other import Collection
from specklepy.transports.server import ServerTransport
from specklepy.core.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.client import SpeckleClient
from specklepy.logging import metrics
import webbrowser

# Initialize Qt resources from file resources.py
from resources import *
from plugin_utils.object_utils import callback, traverseObject
from speckle.converter.geometry.mesh import writeMeshToShp
from speckle.converter.geometry.point import pointToNative
from specklepy.objects.GIS.layers import Layer, VectorLayer, RasterLayer
from speckle.converter.layers import addBimMainThread, addCadMainThread, addRasterMainThread, addVectorMainThread, convertSelectedLayers, getAllLayers, getSavedLayers, getSelectedLayers
from speckle.converter.layers.feature import bimFeatureToNative, cadFeatureToNative
from speckle.converter.layers.symbology import rasterRendererToNative, vectorRendererToNative
from speckle.converter.layers.utils import colorFromSpeckle, findAndClearLayerGroup, tryCreateGroup, trySaveCRS

from specklepy_qt_ui.DataStorage import DataStorage

from speckle.utils.panel_logging import logger
from specklepy_qt_ui.widget_add_stream import AddStreamModalDialog
from specklepy_qt_ui.widget_create_stream import CreateStreamModalDialog
from specklepy_qt_ui.widget_create_branch import CreateBranchModalDialog
from specklepy_qt_ui.logger import logToUser

# Import the code for the dialog
from speckle.utils.validation import tryGetStream, validateBranch, validateCommit, validateStream, validateTransport
from specklepy_qt_ui.widget_custom_crs import CustomCRSDialog 

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

class SpeckleQGIS:
    """Speckle Connector Plugin for QGIS"""

    dockwidget: Optional[QDockWidget]
    version: str
    gis_version: str
    add_stream_modal: AddStreamModalDialog
    create_stream_modal: CreateStreamModalDialog
    current_streams: List[Tuple[StreamWrapper, Stream]]  #{id:(sw,st),id2:()}
    current_layers: List[Tuple[Union[QgsVectorLayer, QgsRasterLayer], str, str]] = []

    active_stream: Optional[Tuple[StreamWrapper, Stream]] 

    qgis_project: QgsProject

    #lat: float
    #lon: float

    accounts: List[Account]

    theads_total: int
    dataStorage: DataStorage

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        
        #self.lock = threading.Lock() 
        self.dockwidget = None
        self.version = "0.0.99"
        self.gis_version = Qgis.QGIS_VERSION.encode('iso-8859-1', errors='ignore').decode('utf-8')
        self.iface = iface
        self.qgis_project = QgsProject.instance()
        self.current_streams = []
        self.active_stream = None
        #self.default_account = None 
        #self.accounts = [] 
        #self.active_account = None 

        self.theads_total = 0

        self.btnAction = 0

        #self.lat = 0.0
        #self.lon = 0.0
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(
            self.plugin_dir, "i18n", "SpeckleQGIS_{}.qm".format(locale)
        )

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr("&SpeckleQGIS")

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.pluginIsActive = False
        

    # noinspection PyMethodMayBeStatic

    def tr(self, message: str):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate("SpeckleQGIS", message)

    def add_action(
        self,
        icon_path: str,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ":/plugins/speckle_qgis/icon.png"
        self.add_action(
            icon_path,
            text=self.tr("SpeckleQGIS"),
            callback=self.run,
            parent=self.iface.mainWindow(),
        )

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # disconnects
        if self.dockwidget:
            try: self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
            except: pass 

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False
        self.dockwidget.close()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        try:
            for action in self.actions:
                self.iface.removePluginWebMenu(self.tr("&SpeckleQGIS"), action)
                self.iface.removeToolBarIcon(action)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def onRunButtonClicked(self):
        print("onRUN")
        # set QGIS threads number only the first time: 
        if self.theads_total==0: self.theads_total = threading.active_count()
        #print(threading.active_count())

        # set the project instance 
        self.qgis_project = QgsProject.instance()
        self.dataStorage.project = self.qgis_project
        self.dockwidget.msgLog.setGeometry(0, 0, self.dockwidget.frameSize().width(), self.dockwidget.frameSize().height())

        # https://www.opengis.ch/2016/09/07/using-threads-in-qgis-python-plugins/
        
        # send 
        if self.btnAction == 0: 
            # Reset Survey point
            #self.dockwidget.populateSurveyPoint(self)
            # Get and clear message
            message = str(self.dockwidget.messageInput.text())
            self.dockwidget.messageInput.setText("")
            
            try:
                streamWrapper = self.active_stream[0]
                client = streamWrapper.get_client()
                self.dataStorage.active_account = client.account
                
                try:
                    metrics.track("Connector Action", self.dataStorage.active_account, {"name": "Toggle Multi-threading Send", "is": True, "connector_version": str(self.version)})
                except Exception as e:
                    logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget )

                t = threading.Thread(target=self.onSend, args=(message,))
                t.start()
            except: self.onSend(message)
        # receive 
        elif self.btnAction == 1: 
            ################### repeated 
            try:
                if not self.dockwidget: return
                # Check if stream id/url is empty
                if self.active_stream is None:
                    logToUser("Please select a stream from the list", level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
                    return
                
                # Get the stream wrapper
                streamWrapper = self.active_stream[0]
                streamId = streamWrapper.stream_id
                client = streamWrapper.get_client()
            except Exception as e:
                logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
                return

            # Ensure the stream actually exists
            try:
                stream = validateStream(streamWrapper, self.dockwidget)
                if stream == None: 
                    return
                
                branchName = str(self.dockwidget.streamBranchDropdown.currentText())
                branch = validateBranch(stream, branchName, True, self.dockwidget)
                if branch == None: 
                    return

                commitId = str(self.dockwidget.commitDropdown.currentText())
                commit = validateCommit(branch, commitId, self.dockwidget)
                if commit == None: 
                    return

                # If group exists, remove layers inside  
                newGroupName = streamId + "_" + branch.name + "_" + commit.id
                newGroupName = removeSpecialCharacters(newGroupName)
                findAndClearLayerGroup(self.qgis_project, newGroupName, commit.id)

            except Exception as e:
                logToUser(str(e), level = 2, func = inspect.stack()[0][3], plugin = self.dockwidget)
                return
            ########################################### end of repeated 
            r'''
            if not self.dockwidget.experimental.isChecked(): 
                
                try:
                    metrics.track("Connector Action", self.dataStorage.active_account, {"name": "Toggle Multi-threading Receive", "is": False, "connector_version": str(self.version)})
                except Exception as e:
                    logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget )
                self.onReceive()
            else:
            '''
            try:
                streamWrapper = self.active_stream[0]
                client = streamWrapper.get_client()
                self.dataStorage.active_account = client.account
                try:
                    metrics.track("Connector Action", self.dataStorage.active_account, {"name": "Toggle Multi-threading Receive", "is": True, "connector_version": str(self.version)})
                except Exception as e:
                    logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget )

                t = threading.Thread(target=self.onReceive, args=())
                t.start()
            except: self.onReceive()

    def onSend(self, message: str):
        """Handles action when Send button is pressed."""
        #logToUser("Some message here", level = 0, func = inspect.stack()[0][3], plugin=self.dockwidget )
        try: 
            if not self.dockwidget: return
            #self.dockwidget.showWait()
            
            projectCRS = self.qgis_project.crs()

            bySelection = True
            if self.dockwidget.layerSendModeDropdown.currentIndex() == 1: 
                bySelection = False 
                layers = getSavedLayers(self)
            else: 
                layers = getSelectedLayers(self) # List[QgsLayerTreeNode]

            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser("Please select a stream from the list", level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget )
                return
            
            # Check if no layers are selected
            if len(layers) == 0: #len(selectedLayerNames) == 0:
                logToUser("No layers selected", level = 1, func = inspect.stack()[0][3], plugin=self.dockwidget)
                return
            self.dataStorage.sending_layers = layers

            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)
            self.dockwidget.mappingSendDialog.populateSavedTransforms(self.dataStorage)
            
            units = str(QgsUnitTypes.encodeUnit(projectCRS.mapUnits())) 
            if units is None or units == 'degrees': units = 'm'
            self.dataStorage.currentUnits = units 

            base_obj = Collection(units = units, collectionType = "QGIS commit", name = "QGIS commit")
            base_obj.elements = convertSelectedLayers(layers, [],[], projectCRS, self)
            if base_obj.elements is None:
                return 

            # Get the stream wrapper
            streamWrapper = self.active_stream[0]
            streamName = self.active_stream[1].name
            streamId = streamWrapper.stream_id
            client = streamWrapper.get_client()

            stream = validateStream(streamWrapper, self.dockwidget)
            if stream == None: 
                return
            
            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, False, self.dockwidget)
            if branch == None: 
                return

            transport = validateTransport(client, streamId)
            if transport == None: 
                return
        
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

        try:
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except SpeckleException as e:
            logToUser("Error sending data: " + str(e.message), level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

        #logToUser("long errror something something msg1", level=2, plugin= self.dockwidget)
        try:
            # you can now create a commit on your stream with this object
            commit_id = client.commit.create(
                stream_id=streamId,
                object_id=objId,
                branch_name=branchName,
                message="Sent objects from QGIS" if len(message) == 0 else message,
                source_application="QGIS " + self.gis_version.split(".")[0],
            )
            
            try:
                metr_filter = "Selected" if bySelection is True else "Saved"
                metr_main = True if branchName=="main" else False
                metr_saved_streams = len(self.current_streams)
                metr_branches = len(self.active_stream[1].branches.items)
                metr_collab = len(self.active_stream[1].collaborators)
                metr_projected = True if not projectCRS.isGeographic() else False
                if self.qgis_project.crs().isValid() is False: metr_projected = None
                
                try:
                    metr_crs = True if self.dataStorage.custom_lat!=0 and self.dataStorage.custom_lon!=0 and str(self.dataStorage.custom_lat) in projectCRS.toWkt() and str(self.dataStorage.custom_lon) in projectCRS.toWkt() else False
                except:
                    metr_crs = False

                metrics.track(metrics.SEND, self.dataStorage.active_account, {"hostAppFullVersion":self.gis_version, "branches":metr_branches, "collaborators":metr_collab,"connector_version": str(self.version), "filter": metr_filter, "isMain": metr_main, "savedStreams": metr_saved_streams, "projectedCRS": metr_projected, "customCRS": metr_crs})
            except:
                metrics.track(metrics.SEND, self.dataStorage.active_account)
            
            
            if isinstance(commit_id, SpeckleException):
                logToUser("Error creating commit: "+str(commit_id.message), level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
                return
            url: str = streamWrapper.stream_url.split("?")[0] + "/commits/" + commit_id
            
            #self.dockwidget.hideWait()
            #self.dockwidget.showLink(url, streamName)
            #if self.dockwidget.experimental.isChecked(): time.sleep(3)

            if self.qgis_project.crs().isGeographic() is True or self.qgis_project.crs().isValid() is False: 
                    logToUser("Data has been sent in the units 'degrees'. It is advisable to set the project CRS to Projected type (e.g. EPSG:32631) to be able to receive geometry correctly in CAD/BIM software. You can also create a custom CRS by setting geographic coordinates and using 'Set as a project center' function.", level = 1, plugin = self.dockwidget)
            
            logToUser(f"👌 Data sent to \"{streamName}\" \n View it online", level = 0, plugin=self.dockwidget, url = url)
            self.dataStorage.sending_layers = None

            return url

        except Exception as e:
            #if self.dockwidget.experimental.isChecked(): 
            time.sleep(1)
            logToUser("Error creating commit: "+str(e), level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)

    def onReceive(self):
        """Handles action when the Receive button is pressed"""
        print("Receive")

        try:
            if not self.dockwidget: return
            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser("Please select a stream from the list", level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
                return
            
            # Get the stream wrapper
            streamWrapper = self.active_stream[0]
            streamId = streamWrapper.stream_id
            client = streamWrapper.get_client()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

        # Ensure the stream actually exists
        try:
            stream = validateStream(streamWrapper, self.dockwidget)
            if stream == None: 
                return
            
            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, True, self.dockwidget)
            if branch == None: 
                return

            commitId = str(self.dockwidget.commitDropdown.currentText())
            commit = validateCommit(branch, commitId, self.dockwidget)
            if commit == None: 
                return

        except Exception as e:
            logToUser(str(e), level = 2, func = inspect.stack()[0][3], plugin = self.dockwidget)
            return
        try:
            objId = commit.referencedObject
            if branch.name is None or commit.id is None or objId is None: 
                return 

            app_full = commit.sourceApplication
            app = getAppName(commit.sourceApplication)
            client_id = client.account.userInfo.id

            transport = validateTransport(client, streamId)
            if transport == None: 
                return 
            commitObj = operations.receive(objId, transport, None)
            
            projectCRS = self.qgis_project.crs()
            try:
                metr_crs = True if self.dataStorage.custom_lat!=0 and self.dataStorage.custom_lon!=0 and str(self.dataStorage.custom_lat) in projectCRS.toWkt() and str(self.dataStorage.custom_lon) in projectCRS.toWkt() else False
            except:
                metr_crs = False
            
            metr_projected = True if not projectCRS.isGeographic() else False
            if self.qgis_project.crs().isValid() is False: metr_projected = None
            try:
                metrics.track(metrics.RECEIVE, self.dataStorage.active_account, {"hostAppFullVersion":self.gis_version, "sourceHostAppVersion": app_full, "sourceHostApp": app, "isMultiplayer": commit.authorId != client_id,"connector_version": str(self.version), "projectedCRS": metr_projected, "customCRS": metr_crs})
            except:
                metrics.track(metrics.RECEIVE, self.dataStorage.active_account)
            
            client.commit.received(
            streamId,
            commit.id,
            source_application="QGIS " + self.gis_version.split(".")[0],
            message="Received commit in QGIS",
            )

            if app.lower() != "qgis" and app.lower() != "arcgis": 
                if self.qgis_project.crs().isGeographic() is True or self.qgis_project.crs().isValid() is False: 
                    logToUser("Conversion from metric units to DEGREES not supported. It is advisable to set the project CRS to Projected type before receiving CAD/BIM geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates", level = 1, func = inspect.stack()[0][3], plugin = self.dockwidget)
            #logger.log(f"Succesfully received {objId}")

        except Exception as e:
            logToUser(str(e), level = 2, func = inspect.stack()[0][3], plugin = self.dockwidget)
            return 
        
        newGroupName = streamId + "_" + branch.name + "_" + commit.id
        newGroupName = removeSpecialCharacters(newGroupName)
        try:
            if app.lower() == "qgis" or app.lower() == "arcgis": check: Callable[[Base], bool] = lambda base: base.speckle_type and (base.speckle_type.endswith("VectorLayer") or base.speckle_type.endswith("Layer") or base.speckle_type.endswith("RasterLayer") )
            else: check: Callable[[Base], bool] = lambda base: (base.speckle_type) # and base.speckle_type.endswith("Base") )
            traverseObject(self, commitObj, callback, check, str(newGroupName))
            
            #if self.dockwidget.experimental.isChecked(): time.sleep(3)
            logToUser("👌 Data received", level = 0, plugin = self.dockwidget, blue = True)
            #return 
            
        except Exception as e:
            #if self.dockwidget.experimental.isChecked(): time.sleep(1)
            logToUser("Receive failed: "+ str(e), level = 2, func = inspect.stack()[0][3], plugin = self.dockwidget)
            return

    def reloadUI(self):
        print("___RELOAD UI")
        try:
            from speckle.utils.project_vars import get_project_streams, get_survey_point, get_rotation, get_crs_offsets, get_project_saved_layers, get_transformations 

            self.qgis_project = QgsProject.instance()
            
            self.dataStorage = DataStorage()
            self.dataStorage.plugin_version = self.version
            self.dataStorage.project = self.qgis_project
        
            get_transformations(self.dataStorage)
            
            
            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)
            self.dockwidget.addDataStorage(self)

            self.is_setup = self.check_for_accounts()

            if self.dockwidget is not None:
                self.active_stream = None
                get_project_streams(self)
                get_rotation(self.dataStorage)
                get_survey_point(self.dataStorage)
                get_crs_offsets(self.dataStorage)
                get_project_saved_layers(self)
                self.dockwidget.populateSavedLayerDropdown(self)

                self.dockwidget.reloadDialogUI(self)

        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def check_for_accounts(self):
        try:
            def go_to_manager():
                webbrowser.open("https://speckle-releases.netlify.app/")
            accounts = get_local_accounts()
            self.dataStorage.accounts = accounts
            if len(accounts) == 0:
                logToUser("No accounts were found. Please remember to install the Speckle Manager and setup at least one account", level = 1, url="https://speckle-releases.netlify.app/", func = inspect.stack()[0][3], plugin = self.dockwidget) #, action_text="Download Manager", callback=go_to_manager)
                return False
            for acc in accounts:
                if acc.isDefault: 
                    self.dataStorage.default_account = acc 
                    self.dataStorage.active_account = acc 
                    break 
            return True
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def run(self):
        """Run method that performs all the real work"""
        from specklepy_qt_ui.dockwidget_main import SpeckleQGISDialog
        from speckle.utils.project_vars import get_project_streams, get_survey_point, get_rotation, get_crs_offsets, get_elevationLayer, get_project_saved_layers, get_transformations

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.qgis_project = QgsProject.instance()
        self.dataStorage = DataStorage()
        self.dataStorage.plugin_version = self.version
        self.dataStorage.project = self.qgis_project
    
        get_transformations(self.dataStorage)

        self.is_setup = self.check_for_accounts()
            
        if self.pluginIsActive:
            self.reloadUI()
        else:
            self.pluginIsActive = True
            if self.dockwidget is None:
                self.dockwidget = SpeckleQGISDialog()

                root = self.dataStorage.project.layerTreeRoot()
                self.dataStorage.all_layers = getAllLayers(root)
                self.dockwidget.addDataStorage(self)
                self.dockwidget.runSetup(self)
                self.dockwidget.createMappingDialog()

                self.qgis_project.fileNameChanged.connect(self.reloadUI)
                self.qgis_project.homePathChanged.connect(self.reloadUI)

                self.dockwidget.runButton.clicked.connect(self.onRunButtonClicked)
                self.dockwidget.runButton.clicked.connect(self.onRunButtonClicked)

                self.dockwidget.crsSettings.clicked.connect(self.customCRSDialogCreate)
                
                self.dockwidget.signal_1.connect(addVectorMainThread)
                self.dockwidget.signal_2.connect(addBimMainThread)
                self.dockwidget.signal_3.connect(addCadMainThread)
                self.dockwidget.signal_4.connect(addRasterMainThread)
                
            else: 
                root = self.dataStorage.project.layerTreeRoot()
                self.dataStorage.all_layers = getAllLayers(root)
                self.dockwidget.addDataStorage(self)

            get_project_streams(self)
            get_rotation(self.dataStorage)
            get_survey_point(self.dataStorage)
            get_crs_offsets(self.dataStorage)
            get_project_saved_layers(self)
            self.dockwidget.populateSavedLayerDropdown(self)
            get_elevationLayer(self.dataStorage)

            self.dockwidget.run(self)
            self.dockwidget.saveLayerSelection.clicked.connect(lambda: self.populateSelectedLayerDropdown())

            # show the dockwidget
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.enableElements(self)
    
    def populateSelectedLayerDropdown(self):
        from speckle.utils.project_vars import set_project_layer_selection
        layers = getSelectedLayers(self)
        current_layers = []
        for layer in layers:
            current_layers.append((layer, layer.name(), ""))
        self.dataStorage.current_layers = current_layers
        self.dockwidget.populateSelectedLayerDropdown(self)
        set_project_layer_selection(self)

    def onStreamAddButtonClicked(self):
        try:
            self.add_stream_modal = AddStreamModalDialog(None)
            self.add_stream_modal.handleStreamAdd.connect(self.handleStreamAdd)
            self.add_stream_modal.show()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    r'''
    def set_survey_point(self): 
        try:
            from speckle.utils.project_vars import set_survey_point, setProjectReferenceSystem
            set_survey_point(self.dataStorage, self.dockwidget)
            setProjectReferenceSystem(self.dataStorage, self.dockwidget)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return
    '''
    
    def onStreamCreateClicked(self):
        try:
            self.create_stream_modal = CreateStreamModalDialog(None)
            self.create_stream_modal.handleStreamCreate.connect(self.handleStreamCreate)
            #self.create_stream_modal.handleCancelStreamCreate.connect(lambda: self.dockwidget.populateProjectStreams(self))
            self.create_stream_modal.show()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return
    
    def handleStreamCreate(self, account, str_name, description, is_public): 
        try:
            new_client = SpeckleClient(
                account.serverInfo.url,
                account.serverInfo.url.startswith("https")
            )
            new_client.authenticate_with_token(token=account.token)

            str_id = new_client.stream.create(name=str_name, description = description, is_public = is_public) 
            if isinstance(str_id, GraphQLException) or isinstance(str_id, SpeckleException):
                logToUser(str_id.message, level = 2, plugin = self.dockwidget)
                return
            else:
                sw = StreamWrapper(account.serverInfo.url + "/streams/" + str_id)
                self.handleStreamAdd(sw)
            return 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def onBranchCreateClicked(self):
        try:
            self.create_stream_modal = CreateBranchModalDialog(None)
            self.create_stream_modal.handleBranchCreate.connect(self.handleBranchCreate)
            self.create_stream_modal.show()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def handleBranchCreate(self, br_name, description):
        try: 
            br_name = br_name.lower()
            sw: StreamWrapper = self.active_stream[0]
            account = sw.get_account()
            new_client = SpeckleClient(
                account.serverInfo.url,
                account.serverInfo.url.startswith("https")
            )
            new_client.authenticate_with_token(token=account.token)
            #description = "No description provided"
            br_id = new_client.branch.create(stream_id = sw.stream_id, name = br_name, description = description) 
            if isinstance(br_id, GraphQLException):
                logToUser(br_id.message, level = 1, plugin = self.dockwidget)

            self.active_stream = (sw, tryGetStream(sw))
            self.current_streams[0] = self.active_stream

            self.dockwidget.populateActiveStreamBranchDropdown(self)
            self.dockwidget.populateActiveCommitDropdown(self)
            self.dockwidget.streamBranchDropdown.setCurrentText(br_name) # will be ignored if branch name is not in the list 

            return 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def handleStreamAdd(self, sw: StreamWrapper):
        try: 
            from speckle.utils.project_vars import set_project_streams
            
            streamExists = 0
            index = 0

            stream = tryGetStream(sw)
            
            for st in self.current_streams: 
                #if isinstance(st[1], SpeckleException) or isinstance(stream, SpeckleException): pass 
                if isinstance(stream, Stream) and st[0].stream_id == stream.id: 
                    streamExists = 1; 
                    break 
                index += 1
        except SpeckleException as e:
            logToUser(e.message, level = 1, plugin=self.dockwidget)
            stream = None
        
        try: 
            if streamExists == 0: 
                self.current_streams.insert(0,(sw, stream))
            else: 
                del self.current_streams[index]
                self.current_streams.insert(0,(sw, stream))
            try: self.add_stream_modal.handleStreamAdd.disconnect(self.handleStreamAdd)
            except: pass 
            set_project_streams(self)
            self.dockwidget.populateProjectStreams(self)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def customCRSDialogCreate(self):
        try:
            
            self.dataStorage.currentCRS = self.dataStorage.project.crs()
            units = str(QgsUnitTypes.encodeUnit(self.dataStorage.project.crs().mapUnits())) 
            self.dataStorage.currentOriginalUnits = units 
            
            if units is None or units == 'degrees': units = 'm'
            self.dataStorage.currentUnits = units 
            
            self.dockwidget.custom_crs_modal = CustomCRSDialog(None)
            self.dockwidget.custom_crs_modal.dataStorage = self.dataStorage
            self.dockwidget.custom_crs_modal.populateModeDropdown()
            self.dockwidget.custom_crs_modal.populateSurveyPoint()
            self.dockwidget.custom_crs_modal.populateOffsets()
            self.dockwidget.custom_crs_modal.populateRotation()

            self.dockwidget.custom_crs_modal.dialog_button_box.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.customCRSApply)
            self.dockwidget.custom_crs_modal.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.crsMoreInfo)
            
            self.dockwidget.custom_crs_modal.show()

        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return
    
    def crsMoreInfo(self):
        import webbrowser
        url = "https://speckle.guide/user/qgis.html#custom-project-center"
        webbrowser.open(url, new=0, autoraise=True)

    def customCRSApply(self):
        index = self.dockwidget.custom_crs_modal.modeDropdown.currentIndex()
        if index == 1: # add offsets
            self.customCRSCreate()
        if index == 0: #create custom CRS
            self.crsOffsetsApply()
        self.applyRotation()
        self.dockwidget.custom_crs_modal.close()

    def applyRotation(self):
        try:
            from speckle.utils.project_vars import set_crs_offsets, set_rotation
            rotate = self.dockwidget.custom_crs_modal.rotation.text() 
            if rotate is not None and rotate != '':
                try:
                    rotate = float(rotate)
                    if not -360<= rotate <=360:
                        logToUser("Angle value must be within the range (-360, 360)", level = 1, plugin=self.dockwidget)
                    else:
                        # warning only if the value changed 
                        if self.dataStorage.crs_rotation != float(rotate):
                            self.dataStorage.crs_rotation = float(rotate)
                            logToUser("Rotation successfully applied", level = 0, plugin=self.dockwidget)
                except: 
                    logToUser("Invalid Angle value", level = 2, plugin=self.dockwidget)
             
            else:
                # warning only if the value changed 
                if self.dataStorage.crs_rotation is not None:
                    self.dataStorage.crs_rotation = None
                    logToUser("Rotation successfully removed", level = 0, plugin=self.dockwidget)
            set_rotation(self.dockwidget.dataStorage, self.dockwidget)
            
        except Exception as e: 
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
                

    def crsOffsetsApply(self):
        try:
            from speckle.utils.project_vars import set_crs_offsets, set_rotation
            offX = self.dockwidget.custom_crs_modal.offsetX.text()
            offY = self.dockwidget.custom_crs_modal.offsetY.text()
            if offX is not None and offX != '' and offY is not None and offY != '':
                try:
                    # warning only if the value changed 
                    if self.dataStorage.crs_offset_x != float(offX) or self.dataStorage.crs_offset_y != float(offY):
                        self.dataStorage.crs_offset_x = float(offX)
                        self.dataStorage.crs_offset_y = float(offY)
                        logToUser("X and Y offsets successfully applied", level = 0, plugin=self.dockwidget)
                except: 
                    logToUser("Invalid Offset values", level = 2, plugin=self.dockwidget)
            
            else: 
                # warning only if the value changed 
                if self.dataStorage.crs_offset_x != None or self.dataStorage.crs_offset_y != None:
                    self.dataStorage.crs_offset_x = None
                    self.dataStorage.crs_offset_y = None
                    logToUser("X and Y offsets successfully removed", level = 0, plugin=self.dockwidget)
            set_crs_offsets(self.dataStorage, self.dockwidget)

        except Exception as e: 
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)

    def customCRSCreate(self):
        try: 
            from speckle.utils.project_vars import set_survey_point, setProjectReferenceSystem
            vals =[ str(self.dockwidget.custom_crs_modal.surveyPointLat.text()), str(self.dockwidget.custom_crs_modal.surveyPointLon.text()) ]
            try:
                custom_lat, custom_lon = [float(i.replace(" ","")) for i in vals]
                
                if custom_lat>180 or custom_lat<-180 or custom_lon >180 or custom_lon<-180:
                    logToUser("LAT LON values must be within (-180, 180). You can right-click on the canvas location to copy coordinates in WGS 84", level = 1, plugin=self.dockwidget)
                    return  
                else: 
                    self.dockwidget.dataStorage.custom_lat = custom_lat
                    self.dockwidget.dataStorage.custom_lon = custom_lon

                    # remove offsets if custom crs applied
                    self.dataStorage.crs_offset_x = None
                    self.dataStorage.crs_offset_y = None
                    self.dockwidget.custom_crs_modal.offsetX.setText('')
                    self.dockwidget.custom_crs_modal.offsetY.setText('')
                    set_survey_point(self.dockwidget.dataStorage, self.dockwidget)
                    setProjectReferenceSystem(self.dockwidget.dataStorage, self.dockwidget)

            except:
                logToUser("Invalid Lat/Lon values", level = 2, plugin=self.dockwidget)


        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return
    