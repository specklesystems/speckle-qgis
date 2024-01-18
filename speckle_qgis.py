# -*- coding: utf-8 -*-

import inspect
import os.path
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from datetime import datetime

import threading
from plugin_utils.threads import KThread
from plugin_utils.helpers import constructCommitURL, getAppName, removeSpecialCharacters
from qgis.core import (
    Qgis,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsUnitTypes,
)
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QApplication,
    QAction,
    QMenu,
    QDockWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt import QtWidgets
from qgis import PyQt

# from PyQt5.QtCore import pyqtSignal

import sip

from specklepy.core.api import operations
from specklepy.logging.exceptions import (
    SpeckleException,
    GraphQLException,
    SpeckleInvalidUnitException,
)
from specklepy.core.api.models import Stream, Branch, Commit
from specklepy.core.api.wrapper import StreamWrapper
from specklepy.objects import Base
from specklepy.objects.other import Collection
from specklepy.objects.units import get_units_from_string
from specklepy.transports.server import ServerTransport
from specklepy.core.api.credentials import (
    Account,
    get_local_accounts,
)  # , StreamWrapper
from specklepy.core.api.client import SpeckleClient
from specklepy.logging import metrics
import webbrowser

# Initialize Qt resources from file resources.py
from resources import *
from plugin_utils.object_utils import callback, traverseObject
from speckle.converter.layers import (
    getAllLayers,
    getAllLayersWithTree,
    getSavedLayers,
    getSelectedLayers,
    getSelectedLayersWithStructure,
)

from speckle.converter.layers.layer_conversions import (
    addBimMainThread,
    addCadMainThread,
    addExcelMainThread,
    addNonGeometryMainThread,
    addRasterMainThread,
    addVectorMainThread,
    convertSelectedLayers,
)
from speckle.converter.layers import findAndClearLayerGroup

from specklepy_qt_ui.qt_ui.DataStorage import DataStorage

# from speckle.utils.panel_logging import logger
from specklepy_qt_ui.qt_ui.widget_add_stream import AddStreamModalDialog
from specklepy_qt_ui.qt_ui.widget_create_stream import CreateStreamModalDialog
from specklepy_qt_ui.qt_ui.widget_create_branch import CreateBranchModalDialog
from speckle.utils.panel_logging import logToUser

# Import the code for the dialog
from speckle.utils.validation import (
    tryGetClient,
    tryGetStream,
    validateBranch,
    validateCommit,
    validateStream,
    validateTransport,
)
from specklepy_qt_ui.qt_ui.widget_custom_crs import CustomCRSDialog

from plugin_utils.installer import _debug

SPECKLE_COLOR = (59, 130, 246)
SPECKLE_COLOR_LIGHT = (69, 140, 255)


class SpeckleQGIS:
    """Speckle Connector Plugin for QGIS"""

    dockwidget: Optional[QDockWidget]
    version: str
    gis_version: str
    add_stream_modal: AddStreamModalDialog
    create_stream_modal: CreateStreamModalDialog
    current_streams: List[Tuple[StreamWrapper, Stream]]  # {id:(sw,st),id2:()}
    current_layers: List[Tuple[Union[QgsVectorLayer, QgsRasterLayer], str, str]] = []
    # current_layer_group: Any
    receive_layer_tree: Dict

    active_stream: Optional[Tuple[StreamWrapper, Stream]]
    active_branch: Optional[Branch] = None
    active_commit: Optional[Commit] = None

    project: QgsProject

    # lat: float
    # lon: float

    accounts: List[Account]

    theads_total: int
    dataStorage: DataStorage
    # signal_groupCreate = pyqtSignal(object)

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface

        # self.lock = threading.Lock()
        self.dockwidget = None
        self.version = "0.0.99"
        self.gis_version = Qgis.QGIS_VERSION.encode(
            "iso-8859-1", errors="ignore"
        ).decode("utf-8")
        self.iface = iface
        self.project = QgsProject.instance()
        self.current_streams = []
        self.active_stream = None
        self.active_branch = None
        self.active_commit = None
        self.receive_layer_tree = None
        # self.default_account = None
        # self.accounts = []
        # self.active_account = None

        self.theads_total = 0

        self.btnAction = 0

        # self.lat = 0.0
        # self.lon = 0.0
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
            try:
                self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
            except:
                pass

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
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def onRunButtonClicked(self):
        # print("onRUN")
        # set QGIS threads number only the first time:
        # if self.theads_total==0: self.theads_total = threading.active_count()

        all_threads = threading.enumerate()

        for t in all_threads:
            if t.name.startswith("speckle"):
                name = ""
                if "receive" in t.name:
                    name = "Receive"
                if "send" in t.name:
                    name = "Send"
                logToUser(
                    f"Previous {name} operation is still running",
                    level=2,
                    plugin=self.dockwidget,
                )
                return

        # set the project instance
        self.project = QgsProject.instance()
        self.dataStorage.project = self.project
        self.dockwidget.msgLog.setGeometry(
            0,
            0,
            self.dockwidget.frameSize().width(),
            self.dockwidget.frameSize().height(),
        )

        self.dockwidget.reportBtn.setEnabled(True)

        # https://www.opengis.ch/2016/09/07/using-threads-in-qgis-python-plugins/

        # send
        if self.btnAction == 0:
            # Reset Survey point
            # self.dockwidget.populateSurveyPoint(self)
            # Get and clear message
            message = str(self.dockwidget.messageInput.text())
            self.dockwidget.messageInput.setText("")

            try:
                streamWrapper = self.active_stream[0]
                client = streamWrapper.get_client()
                self.dataStorage.active_account = client.account
                logToUser(
                    f"Sending data... \nClick here to cancel",
                    level=0,
                    url="cancel",
                    plugin=self.dockwidget,
                )

                if _debug is True:
                    raise Exception
                t = KThread(target=self.onSend, name="speckle_send", args=(message,))
                t.start()
            except:
                self.onSend(message)

        # receive
        elif self.btnAction == 1:
            ################### repeated
            try:
                if not self.dockwidget:
                    return
                # Check if stream id/url is empty
                if self.active_stream is None:
                    logToUser(
                        "Please select a stream from the list",
                        level=2,
                        func=inspect.stack()[0][3],
                        plugin=self.dockwidget,
                    )
                    return

                # Get the stream wrapper
                streamWrapper = self.active_stream[0]
                streamId = streamWrapper.stream_id

                # client = streamWrapper.get_client()
                client, stream = tryGetClient(
                    streamWrapper, self.dataStorage, False, self.dockwidget
                )
                stream = validateStream(stream, self.dockwidget)
                if stream == None:
                    return
            except Exception as e:
                logToUser(
                    e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
                )
                return

            # Ensure the stream actually exists
            try:
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
                findAndClearLayerGroup(self.project.layerTreeRoot(), newGroupName, self)

            except Exception as e:
                logToUser(
                    str(e), level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
                )
                return
            ########################################### end of repeated

            try:
                streamWrapper = self.active_stream[0]
                client = streamWrapper.get_client()
                self.dataStorage.active_account = client.account
                logToUser(
                    "Receiving data... \nClick here to cancel",
                    level=0,
                    url="cancel",
                    plugin=self.dockwidget,
                )

                if _debug is True:
                    raise Exception
                t = KThread(target=self.onReceive, name="speckle_receive", args=())
                t.start()
            except:
                self.onReceive()

    def onSend(self, message: str):
        """Handles action when Send button is pressed."""
        # logToUser("Some message here", level = 0, func = inspect.stack()[0][3], plugin=self.dockwidget )
        try:
            if not self.dockwidget:
                return

            projectCRS = self.project.crs()

            bySelection = True
            if self.dockwidget.layerSendModeDropdown.currentIndex() == 1:
                bySelection = False
                layers, tree_structure = getSavedLayers(self)
            else:
                # layers = getSelectedLayers(self) # List[QgsLayerTreeNode]
                layers, tree_structure = getSelectedLayersWithStructure(self)

            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser(
                    "Please select a stream from the list",
                    level=2,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return

            # Check if no layers are selected
            if len(layers) == 0 or layers is None:  # len(selectedLayerNames) == 0:
                logToUser(
                    "No valid layers selected",
                    level=1,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return
            self.dataStorage.latestActionLayers = [l.name() for l in layers]
            # print(layers)

            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)
            self.dockwidget.mappingSendDialog.populateSavedTransforms(self.dataStorage)

            units = str(QgsUnitTypes.encodeUnit(projectCRS.mapUnits()))
            self.dataStorage.latestActionUnits = units
            try:
                units = get_units_from_string(units)
            except SpeckleInvalidUnitException:
                units = "none"
            self.dataStorage.currentUnits = units

            if (
                self.dataStorage.crs_offset_x is not None
                and self.dataStorage.crs_offset_x
            ) != 0 or (
                self.dataStorage.crs_offset_y is not None
                and self.dataStorage.crs_offset_y
            ):
                logToUser(
                    f"Applying CRS offsets: x={self.dataStorage.crs_offset_x}, y={self.dataStorage.crs_offset_y}",
                    level=0,
                    plugin=self.dockwidget,
                )
            if (
                self.dataStorage.crs_rotation is not None
                and self.dataStorage.crs_rotation
            ) != 0:
                logToUser(
                    f"Applying CRS rotation: {self.dataStorage.crs_rotation}°",
                    level=0,
                    plugin=self.dockwidget,
                )

            self.dataStorage.latestActionReport = []
            self.dataStorage.latestActionFeaturesReport = []
            base_obj = Collection(
                units=units,
                collectionType="QGIS commit",
                name="QGIS commit",
                elements=[],
            )

            # conversions
            time_start_conversion = datetime.now()
            base_obj = convertSelectedLayers(
                base_obj, layers, tree_structure, projectCRS, self
            )
            time_end_conversion = datetime.now()

            if (
                base_obj is None
                or base_obj.elements is None
                or (isinstance(base_obj.elements, List) and len(base_obj.elements) == 0)
            ):
                logToUser(f"No data to send", level=2, plugin=self.dockwidget)
                return

            logToUser(f"Sending data to the server...", level=0, plugin=self.dockwidget)
            # Get the stream wrapper
            streamWrapper = self.active_stream[0]
            streamName = self.active_stream[1].name
            streamId = streamWrapper.stream_id
            # client = streamWrapper.get_client()
            client, stream = tryGetClient(
                streamWrapper, self.dataStorage, True, self.dockwidget
            )
            if not isinstance(client, SpeckleClient) or not isinstance(stream, Stream):
                return

            stream = validateStream(stream, self.dockwidget)
            if not isinstance(stream, Stream):
                return

            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, False, self.dockwidget)
            branchId = branch.id
            if branch == None:
                return

            transport = validateTransport(client, streamId)
            if transport == None:
                return

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

        # data transfer

        self.dockwidget.signal_remove_btn_url.emit("cancel")
        time_start_transfer = datetime.now()
        try:
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except Exception as e:
            logToUser(
                "Error sending data: " + str(e),
                level=2,
                func=inspect.stack()[0][3],
                plugin=self.dockwidget,
            )
            return
        time_end_transfer = datetime.now()

        try:
            # you can now create a commit on your stream with this object
            commit_id = client.commit.create(
                stream_id=streamId,
                object_id=objId,
                branch_name=branchName,
                message="Sent objects from QGIS" if len(message) == 0 else message,
                source_application="QGIS" + self.gis_version.split(".")[0],
            )

            # add time stats to the report
            self.dataStorage.latestActionTime = str(
                datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            )
            self.dataStorage.latestTransferTime = str(
                time_end_transfer - time_start_transfer
            )
            self.dataStorage.latestConversionTime = str(
                time_end_conversion - time_start_conversion
            )
            try:
                metr_filter = "Selected" if bySelection is True else "Saved"
                metr_main = True if branchName == "main" else False
                metr_saved_streams = len(self.current_streams)
                metr_branches = len(self.active_stream[1].branches.items)
                metr_collab = len(self.active_stream[1].collaborators)
                metr_projected = True if not projectCRS.isGeographic() else False
                if self.project.crs().isValid() is False:
                    metr_projected = None

                try:
                    metr_crs = (
                        True
                        if self.dataStorage.custom_lat != 0
                        and self.dataStorage.custom_lon != 0
                        and str(self.dataStorage.custom_lat) in projectCRS.toWkt()
                        and str(self.dataStorage.custom_lon) in projectCRS.toWkt()
                        else False
                    )
                except:
                    metr_crs = False

                metrics.track(
                    metrics.SEND,
                    self.dataStorage.active_account,
                    {
                        "hostAppFullVersion": self.gis_version,
                        "branches": metr_branches,
                        "collaborators": metr_collab,
                        "connector_version": str(self.version),
                        "filter": metr_filter,
                        "isMain": metr_main,
                        "savedStreams": metr_saved_streams,
                        "projectedCRS": metr_projected,
                        "customCRS": metr_crs,
                        "time_conversion": (
                            time_end_conversion - time_start_conversion
                        ).total_seconds(),
                        "time_transfer": (
                            time_end_transfer - time_start_transfer
                        ).total_seconds(),
                    },
                )
            except:
                metrics.track(metrics.SEND, self.dataStorage.active_account)

            if isinstance(commit_id, SpeckleException):
                logToUser(
                    "Error creating commit: " + str(commit_id.message),
                    level=2,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return
            url: str = constructCommitURL(streamWrapper, branchId, commit_id)

            if str(self.dockwidget.commitDropdown.currentText()).startswith("Latest"):
                stream = client.stream.get(
                    id=streamId, branch_limit=100, commit_limit=100
                )
                branch = validateBranch(stream, branchName, False, self.dockwidget)
                self.active_commit = branch.commits.items[0]

            # self.dockwidget.hideWait()
            # self.dockwidget.showLink(url, streamName)
            # if self.dockwidget.experimental.isChecked(): time.sleep(3)

            if (
                self.project.crs().isGeographic() is True
                or self.project.crs().isValid() is False
            ):
                logToUser(
                    "Data has been sent in the units 'degrees'. It is advisable to set the project CRS to Projected type (e.g. EPSG:32631) to be able to receive geometry correctly in CAD/BIM software. You can also create a custom CRS by setting geographic coordinates and using 'Set as a project center' function.",
                    level=1,
                    plugin=self.dockwidget,
                )

            self.dockwidget.msgLog.dataStorage = self.dataStorage

            logToUser(
                "Data sent to '"
                + str(streamName)
                + "'"
                + "\nClick to view commit online",
                level=0,
                plugin=self.dockwidget,
                url=url,
                report=True,
            )

        except Exception as e:
            # if self.dockwidget.experimental.isChecked():
            time.sleep(1)
            logToUser(
                "Error creating commit: " + str(e),
                level=2,
                func=inspect.stack()[0][3],
                plugin=self.dockwidget,
            )

        self.dockwidget.cancelOperations()

    def onReceive(self):
        """Handles action when the Receive button is pressed"""
        # print("Receive")

        try:
            if not self.dockwidget:
                return

            self.dataStorage.latestHostApp = ""

            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser(
                    "Please select a stream from the list",
                    level=2,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return

            # Get the stream wrapper
            streamWrapper = self.active_stream[0]
            streamId = streamWrapper.stream_id

            # client = streamWrapper.get_client()
            client, stream = tryGetClient(
                streamWrapper, self.dataStorage, False, self.dockwidget
            )
            if not isinstance(client, SpeckleClient) or not isinstance(stream, Stream):
                return
            stream = validateStream(stream, self.dockwidget)
            if not isinstance(stream, Stream):
                return

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

        # Ensure the stream actually exists
        try:
            branchName = str(self.dockwidget.streamBranchDropdown.currentText())

            if str(self.dockwidget.commitDropdown.currentText()).startswith("Latest"):
                stream = client.stream.get(
                    id=stream.id, branch_limit=100, commit_limit=100
                )

            branch = validateBranch(stream, branchName, True, self.dockwidget)
            if branch == None:
                return

            commitId = str(self.dockwidget.commitDropdown.currentText())
            commit = validateCommit(branch, commitId, self.dockwidget)
            if commit == None:
                return
            self.active_commit = commit

        except Exception as e:
            logToUser(
                str(e), level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
            )
            return
        try:
            objId = commit.referencedObject
            if branch.name is None or commit.id is None or objId is None:
                return

            app_full = commit.sourceApplication
            app = getAppName(commit.sourceApplication)
            self.dataStorage.latestHostApp = app
            client_id = client.account.userInfo.id

            transport = validateTransport(client, streamId)
            if transport == None:
                logToUser(
                    "Transport not found",
                    level=2,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return

            # data transfer
            time_start_transfer = datetime.now()
            commitObj = operations.receive(objId, transport, None)
            time_end_transfer = datetime.now()
            self.dockwidget.signal_remove_btn_url.emit("cancel")

            projectCRS = self.project.crs()
            units = str(QgsUnitTypes.encodeUnit(projectCRS.mapUnits()))
            self.dataStorage.latestActionUnits = units

            try:
                metr_crs = (
                    True
                    if self.dataStorage.custom_lat != 0
                    and self.dataStorage.custom_lon != 0
                    and str(self.dataStorage.custom_lat) in projectCRS.toWkt()
                    and str(self.dataStorage.custom_lon) in projectCRS.toWkt()
                    else False
                )
            except:
                metr_crs = False

            metr_projected = True if not projectCRS.isGeographic() else False
            if self.project.crs().isValid() is False:
                metr_projected = None

            client.commit.received(
                streamId,
                commit.id,
                source_application="QGIS" + self.gis_version.split(".")[0],
                message="Received commit in QGIS",
            )

            if app.lower() != "qgis" and app.lower() != "arcgis":
                if (
                    self.project.crs().isGeographic() is True
                    or self.project.crs().isValid() is False
                ):
                    logToUser(
                        "Conversion from metric units to DEGREES not supported. It is advisable to set the project CRS to Projected type before receiving CAD/BIM geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates",
                        level=1,
                        func=inspect.stack()[0][3],
                        plugin=self.dockwidget,
                    )

        except Exception as e:
            logToUser(
                str(e), level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
            )
            return

        newGroupName = streamId + "_" + branch.name + "_" + commit.id
        newGroupName = removeSpecialCharacters(newGroupName)
        try:
            if app.lower() != "qgis" and app.lower() != "arcgis":
                if (
                    self.dataStorage.crs_offset_x is not None
                    and self.dataStorage.crs_offset_x
                ) != 0 or (
                    self.dataStorage.crs_offset_y is not None
                    and self.dataStorage.crs_offset_y
                ):
                    logToUser(
                        f"Applying CRS offsets: x={self.dataStorage.crs_offset_x}, y={self.dataStorage.crs_offset_y}",
                        level=0,
                        plugin=self.dockwidget,
                    )
                if (
                    self.dataStorage.crs_rotation is not None
                    and self.dataStorage.crs_rotation
                ) != 0:
                    logToUser(
                        f"Applying CRS rotation: {self.dataStorage.crs_rotation}°",
                        level=0,
                        plugin=self.dockwidget,
                    )
        except:
            pass

        try:
            if app.lower() == "qgis" or app.lower() == "arcgis":
                # print(app.lower())
                check: Callable[[Base], bool] = lambda base: base.speckle_type and (
                    base.speckle_type.endswith("VectorLayer")
                    or base.speckle_type.endswith("Layer")
                    or base.speckle_type.endswith("RasterLayer")
                )
            else:
                check: Callable[[Base], bool] = lambda base: (
                    base.speckle_type
                )  # and base.speckle_type.endswith("Base") )
            self.receive_layer_tree = {str(newGroupName): {}}
            # print(self.receive_layer_tree)

            self.dataStorage.latestActionLayers = []
            self.dataStorage.latestActionReport = []

            # conversions
            time_start_conversion = (
                self.dataStorage.latestConversionTime
            ) = datetime.now()
            traverseObject(self, commitObj, callback, check, str(newGroupName), "")
            time_end_conversion = self.dataStorage.latestConversionTime

            # add time stats to the report
            self.dataStorage.latestActionTime = str(
                datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            )
            self.dataStorage.latestTransferTime = str(
                time_end_transfer - time_start_transfer
            )

            self.dockwidget.msgLog.dataStorage = self.dataStorage
            # if self.dockwidget.experimental.isChecked(): time.sleep(3)
            logToUser(
                "Data received",
                level=0,
                plugin=self.dockwidget,
                blue=True,
                report=True,
            )

            try:
                metrics.track(
                    metrics.RECEIVE,
                    self.dataStorage.active_account,
                    {
                        "hostAppFullVersion": self.gis_version,
                        "sourceHostAppVersion": app_full,
                        "sourceHostApp": app,
                        "isMultiplayer": commit.authorId != client_id,
                        "connector_version": str(self.version),
                        "projectedCRS": metr_projected,
                        "customCRS": metr_crs,
                        "time_transfer": (
                            time_end_transfer - time_start_transfer
                        ).total_seconds(),
                    },
                )
            except:
                metrics.track(metrics.RECEIVE, self.dataStorage.active_account)

        except Exception as e:
            # if self.dockwidget.experimental.isChecked(): time.sleep(1)
            logToUser(
                "Receive failed: " + str(e),
                level=2,
                func=inspect.stack()[0][3],
                plugin=self.dockwidget,
            )

        self.dockwidget.cancelOperations()

    def reloadUI(self):
        print("___RELOAD UI")
        try:
            self.dockwidget.signal_cancel_operation.emit()
            # self.dockwidget.cancelOperations()
            from speckle.utils.project_vars import (
                get_project_streams,
                get_survey_point,
                get_rotation,
                get_crs_offsets,
                get_project_saved_layers,
                get_transformations,
            )

            self.project = QgsProject.instance()

            self.dataStorage = DataStorage()
            self.dataStorage.plugin_version = self.version
            self.dataStorage.project = self.project

            get_transformations(self.dataStorage)

            root = self.dataStorage.project.layerTreeRoot()
            self.dataStorage.all_layers = getAllLayers(root)
            self.dockwidget.addDataStorage(self)

            self.is_setup = self.dataStorage.check_for_accounts()

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
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def run(self):
        """Run method that performs all the real work"""
        from speckle.ui_widgets.dockwidget_main import SpeckleQGISDialog
        from speckle.utils.project_vars import (
            get_project_streams,
            get_survey_point,
            get_rotation,
            get_crs_offsets,
            get_elevationLayer,
            get_project_saved_layers,
            get_transformations,
        )

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.project = QgsProject.instance()
        self.dataStorage = DataStorage()
        self.dataStorage.plugin_version = self.version
        self.dataStorage.project = self.project

        get_transformations(self.dataStorage)

        self.is_setup = self.dataStorage.check_for_accounts()

        if self.pluginIsActive:
            self.reloadUI()
        else:
            print("Plugin inactive, launch")
            self.pluginIsActive = True
            if self.dockwidget is None:
                self.dockwidget = SpeckleQGISDialog()

                root = self.dataStorage.project.layerTreeRoot()
                self.dataStorage.all_layers = getAllLayers(root)
                self.dockwidget.addDataStorage(self)
                self.dockwidget.runSetup(self)
                self.dockwidget.createMappingDialog()

                self.project.fileNameChanged.connect(self.reloadUI)
                self.project.homePathChanged.connect(self.reloadUI)

                self.dockwidget.runButton.clicked.connect(self.onRunButtonClicked)

                self.dockwidget.crsSettings.clicked.connect(self.customCRSDialogCreate)

                self.dockwidget.signal_1.connect(addVectorMainThread)
                self.dockwidget.signal_2.connect(addBimMainThread)
                self.dockwidget.signal_3.connect(addCadMainThread)
                self.dockwidget.signal_4.connect(addRasterMainThread)
                self.dockwidget.signal_5.connect(addNonGeometryMainThread)
                self.dockwidget.signal_6.connect(addExcelMainThread)
                self.dockwidget.signal_remove_btn_url.connect(
                    self.dockwidget.msgLog.removeBtnUrl
                )
                self.dockwidget.signal_cancel_operation.connect(
                    self.dockwidget.cancelOperations
                )

                # self.signal_groupCreate.connect(tryCreateGroup)

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
            self.dockwidget.saveLayerSelection.clicked.connect(
                lambda: self.populateSelectedLayerDropdown()
            )

            # show the dockwidget
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.enableElements(self)

        import urllib3
        import requests

        # if the standard QGIS libraries are used
        if (urllib3.__version__ == "1.25.11" and requests.__version__ == "2.24.0") or (
            urllib3.__version__.startswith("1.24.")
            and requests.__version__.startswith("2.23.")
        ):
            logToUser(
                "Dependencies versioning error.\nClick here for details.",
                url="dependencies_error",
                level=2,
                plugin=self.dockwidget,
            )

    def populateSelectedLayerDropdown(self):
        # print("populateSelectedLayerDropdown")
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
            self.add_stream_modal.dataStorage = self.dataStorage
            self.add_stream_modal.connect()
            # self.add_stream_modal.onAccountSelected(0)
            self.add_stream_modal.handleStreamAdd.connect(self.handleStreamAdd)
            # self.add_stream_modal.getAllStreams()
            self.add_stream_modal.show()
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    r"""
    def set_survey_point(self): 
        try:
            from speckle.utils.project_vars import set_survey_point, setProjectReferenceSystem
            set_survey_point(self.dataStorage, self.dockwidget)
            setProjectReferenceSystem(self.dataStorage, self.dockwidget)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
            return
    """

    def onStreamCreateClicked(self):
        try:
            self.create_stream_modal = CreateStreamModalDialog(None)
            self.create_stream_modal.handleStreamCreate.connect(self.handleStreamCreate)
            # self.create_stream_modal.handleCancelStreamCreate.connect(lambda: self.dockwidget.populateProjectStreams(self))
            self.create_stream_modal.show()
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def handleStreamCreate(self, account, str_name, description, is_public):
        try:
            new_client = SpeckleClient(
                account.serverInfo.url, account.serverInfo.url.startswith("https")
            )
            try:
                new_client.authenticate_with_token(token=account.token)
            except SpeckleException as ex:
                if "already connected" in ex.message:
                    logToUser(
                        "Dependencies versioning error.\nClick here for details.",
                        url="dependencies_error",
                        level=2,
                        plugin=self.dockwidget,
                    )
                    return
                else:
                    raise ex

            str_id = new_client.stream.create(
                name=str_name, description=description, is_public=is_public
            )

            try:
                metrics.track(
                    "Connector Action",
                    self.dataStorage.active_account,
                    {
                        "name": "Stream Create",
                        "connector_version": str(self.dataStorage.plugin_version),
                    },
                )
            except Exception as e:
                logToUser(
                    e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
                )

            if isinstance(str_id, GraphQLException) or isinstance(
                str_id, SpeckleException
            ):
                logToUser(str_id.message, level=2, plugin=self.dockwidget)
                return
            else:
                sw = StreamWrapper(account.serverInfo.url + "/streams/" + str_id)
                self.handleStreamAdd((sw, None, None))
            return
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def onBranchCreateClicked(self):
        try:
            self.create_stream_modal = CreateBranchModalDialog(None)
            self.create_stream_modal.handleBranchCreate.connect(self.handleBranchCreate)
            self.create_stream_modal.show()
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def handleBranchCreate(self, br_name, description):
        try:
            br_name = br_name.lower()
            sw: StreamWrapper = self.active_stream[0]
            new_client, stream = tryGetClient(
                sw, self.dataStorage, True, self.dockwidget
            )
            account = new_client.account

            try:
                new_client.authenticate_with_token(token=account.token)
            except SpeckleException as ex:
                if "already connected" in ex.message:
                    logToUser(
                        "Dependencies versioning error.\nClick here for details.",
                        url="dependencies_error",
                        level=2,
                        plugin=self.dockwidget,
                    )
                    return
                else:
                    raise ex

            br_id = new_client.branch.create(
                stream_id=sw.stream_id, name=br_name, description=description
            )

            try:
                metrics.track(
                    "Connector Action",
                    self.dataStorage.active_account,
                    {"name": "Branch Create", "connector_version": str(self.version)},
                )
            except Exception as e:
                logToUser(
                    e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
                )

            if isinstance(br_id, GraphQLException):
                logToUser(br_id.message, level=1, plugin=self.dockwidget)

            self.dataStorage.check_for_accounts()
            self.active_stream = (
                sw,
                tryGetStream(sw, self.dataStorage, False, self.dockwidget),
            )
            self.current_streams[0] = self.active_stream

            self.dockwidget.populateActiveStreamBranchDropdown(self)
            self.dockwidget.populateActiveCommitDropdown(self)
            self.dockwidget.streamBranchDropdown.setCurrentText(
                br_name
            )  # will be ignored if branch name is not in the list

            return
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def handleStreamAdd(self, objectPacked: Tuple):
        try:
            # print("___handleStreamAdd")
            from speckle.utils.project_vars import set_project_streams

            sw, branch, commit = objectPacked
            # print(sw)
            # print(branch)
            # print(commit)
            streamExists = 0
            index = 0

            self.dataStorage.check_for_accounts()
            stream = sw.get_client().stream.get(
                id=sw.stream_id, branch_limit=100, commit_limit=100
            )
            # stream = tryGetStream(sw, self.dataStorage, False, self.dockwidget)
            # print(stream)

            if stream is not None and branch in stream.branches.items:
                self.active_branch = branch
                self.active_commit = commit
            else:
                self.active_branch = None
                self.active_commit = None

            # try: print(f"ACTIVE BRANCH NAME: {self.active_branch.name}")
            # except: print("ACTIVE BRANCH IS NONE")
            for st in self.current_streams:
                # if isinstance(st[1], SpeckleException) or isinstance(stream, SpeckleException): pass
                if isinstance(stream, Stream) and st[0].stream_id == stream.id:
                    streamExists = 1
                    break
                index += 1
        except SpeckleException as e:
            logToUser(e.message, level=1, plugin=self.dockwidget)
            stream = None

        try:
            if streamExists == 0:
                self.current_streams.insert(0, (sw, stream))
            else:
                del self.current_streams[index]
                self.current_streams.insert(0, (sw, stream))
            try:
                self.add_stream_modal.handleStreamAdd.disconnect(self.handleStreamAdd)
            except:
                pass
            # set_project_streams(self)
            self.dockwidget.populateProjectStreams(self)
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def customCRSDialogCreate(self):
        try:
            self.dataStorage.currentCRS = self.dataStorage.project.crs()
            units = str(
                QgsUnitTypes.encodeUnit(self.dataStorage.project.crs().mapUnits())
            )
            self.dataStorage.currentOriginalUnits = units

            if units is None or units == "degrees":
                units = "m"
            self.dataStorage.currentUnits = units

            self.dockwidget.custom_crs_modal = CustomCRSDialog(None)
            self.dockwidget.custom_crs_modal.dataStorage = self.dataStorage
            self.dockwidget.custom_crs_modal.populateModeDropdown()
            self.dockwidget.custom_crs_modal.populateSurveyPoint()
            self.dockwidget.custom_crs_modal.populateOffsets()
            self.dockwidget.custom_crs_modal.populateRotation()

            self.dockwidget.custom_crs_modal.dialog_button_box.button(
                QtWidgets.QDialogButtonBox.Apply
            ).clicked.connect(self.customCRSApply)
            crs_info_url = "https://speckle.guide/user/qgis.html#custom-project-center"
            self.dockwidget.custom_crs_modal.dialog_button_box.button(
                QtWidgets.QDialogButtonBox.Cancel
            ).clicked.connect(lambda: self.openUrl(crs_info_url))

            self.dockwidget.custom_crs_modal.show()

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def openUrl(self, url: str = ""):
        import webbrowser

        # url = "https://speckle.guide/user/qgis.html#custom-project-center"
        try:
            if "/commits/" in url or "/models/" in url:
                metrics.track(
                    "Connector Action",
                    self.dataStorage.active_account,
                    {
                        "name": "Open In Web",
                        "connector_version": str(self.dataStorage.plugin_version),
                        "data": "Commit",
                    },
                )
            else:
                metrics.track(
                    "Connector Action",
                    self.dataStorage.active_account,
                    {
                        "name": "Open In Web",
                        "connector_version": str(self.dataStorage.plugin_version),
                    },
                )
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])

        if url is not None and url != "":
            webbrowser.open(url, new=0, autoraise=True)

    def customCRSApply(self):
        index = self.dockwidget.custom_crs_modal.modeDropdown.currentIndex()
        if index == 1:  # add offsets
            self.customCRSCreate()
        if index == 0:  # create custom CRS
            self.crsOffsetsApply()
        self.applyRotation()
        self.dockwidget.custom_crs_modal.close()

    def applyRotation(self):
        try:
            from speckle.utils.project_vars import set_crs_offsets, set_rotation

            rotate = self.dockwidget.custom_crs_modal.rotation.text()
            if rotate is not None and rotate != "":
                try:
                    rotate = float(rotate)
                    if not -360 <= rotate <= 360:
                        logToUser(
                            "Angle value must be within the range (-360, 360)",
                            level=1,
                            plugin=self.dockwidget,
                        )
                    else:
                        # warning only if the value changed
                        if self.dataStorage.crs_rotation != float(rotate):
                            self.dataStorage.crs_rotation = float(rotate)
                            logToUser(
                                "Rotation successfully applied",
                                level=0,
                                plugin=self.dockwidget,
                            )

                            try:
                                metrics.track(
                                    "Connector Action",
                                    self.dataStorage.active_account,
                                    {
                                        "name": "CRS Rotation Add",
                                        "connector_version": str(
                                            self.dataStorage.plugin_version
                                        ),
                                    },
                                )
                            except Exception as e:
                                logToUser(e, level=2, func=inspect.stack()[0][3])

                except:
                    logToUser("Invalid Angle value", level=2, plugin=self.dockwidget)

            else:
                # warning only if the value changed
                if self.dataStorage.crs_rotation is not None:
                    self.dataStorage.crs_rotation = None
                    logToUser(
                        "Rotation successfully removed", level=0, plugin=self.dockwidget
                    )

                    try:
                        metrics.track(
                            "Connector Action",
                            self.dataStorage.active_account,
                            {
                                "name": "CRS Rotation Remove",
                                "connector_version": str(
                                    self.dataStorage.plugin_version
                                ),
                            },
                        )
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

            set_rotation(self.dockwidget.dataStorage, self.dockwidget)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)

    def crsOffsetsApply(self):
        try:
            from speckle.utils.project_vars import set_crs_offsets, set_rotation

            offX = self.dockwidget.custom_crs_modal.offsetX.text()
            offY = self.dockwidget.custom_crs_modal.offsetY.text()
            if offX is not None and offX != "" and offY is not None and offY != "":
                try:
                    # warning only if the value changed
                    if self.dataStorage.crs_offset_x != float(
                        offX
                    ) or self.dataStorage.crs_offset_y != float(offY):
                        self.dataStorage.crs_offset_x = float(offX)
                        self.dataStorage.crs_offset_y = float(offY)
                        logToUser(
                            "X and Y offsets successfully applied",
                            level=0,
                            plugin=self.dockwidget,
                        )

                        try:
                            metrics.track(
                                "Connector Action",
                                self.dataStorage.active_account,
                                {
                                    "name": "CRS Offset Add",
                                    "connector_version": str(
                                        self.dataStorage.plugin_version
                                    ),
                                },
                            )
                        except Exception as e:
                            logToUser(e, level=2, func=inspect.stack()[0][3])

                except:
                    logToUser("Invalid Offset values", level=2, plugin=self.dockwidget)

            else:
                # warning only if the value changed
                if (
                    self.dataStorage.crs_offset_x != None
                    or self.dataStorage.crs_offset_y != None
                ):
                    self.dataStorage.crs_offset_x = None
                    self.dataStorage.crs_offset_y = None
                    logToUser(
                        "X and Y offsets successfully removed",
                        level=0,
                        plugin=self.dockwidget,
                    )

                    try:
                        metrics.track(
                            "Connector Action",
                            self.dataStorage.active_account,
                            {
                                "name": "CRS Offset Remove",
                                "connector_version": str(
                                    self.dataStorage.plugin_version
                                ),
                            },
                        )
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

            set_crs_offsets(self.dataStorage, self.dockwidget)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)

    def customCRSCreate(self):
        try:
            from speckle.utils.project_vars import (
                set_survey_point,
                set_crs_offsets,
                setProjectReferenceSystem,
            )

            vals = [
                str(self.dockwidget.custom_crs_modal.surveyPointLat.text()),
                str(self.dockwidget.custom_crs_modal.surveyPointLon.text()),
            ]
            try:
                custom_lat, custom_lon = [float(i.replace(" ", "")) for i in vals]

                if (
                    custom_lat > 180
                    or custom_lat < -180
                    or custom_lon > 180
                    or custom_lon < -180
                ):
                    logToUser(
                        "LAT LON values must be within (-180, 180). You can right-click on the canvas location to copy coordinates in WGS 84",
                        level=1,
                        plugin=self.dockwidget,
                    )
                    return
                else:
                    self.dockwidget.dataStorage.custom_lat = custom_lat
                    self.dockwidget.dataStorage.custom_lon = custom_lon

                    set_survey_point(self.dockwidget.dataStorage, self.dockwidget)
                    setProjectReferenceSystem(
                        self.dockwidget.dataStorage, self.dockwidget
                    )

                    # remove offsets if custom crs applied
                    if (
                        self.dataStorage.crs_offset_x != None
                        and self.dataStorage.crs_offset_x != 0
                    ) or (
                        self.dataStorage.crs_offset_y != None
                        and self.dataStorage.crs_offset_y != 0
                    ):
                        self.dataStorage.crs_offset_x = None
                        self.dataStorage.crs_offset_y = None
                        self.dockwidget.custom_crs_modal.offsetX.setText("")
                        self.dockwidget.custom_crs_modal.offsetY.setText("")
                        set_crs_offsets(self.dataStorage, self.dockwidget)
                        logToUser(
                            "X and Y offsets removed", level=0, plugin=self.dockwidget
                        )

                    try:
                        metrics.track(
                            "Connector Action",
                            self.dataStorage.active_account,
                            {
                                "name": "CRS Custom Create",
                                "connector_version": str(
                                    self.dataStorage.plugin_version
                                ),
                            },
                        )
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

            except:
                logToUser("Invalid Lat/Lon values", level=2, plugin=self.dockwidget)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return
