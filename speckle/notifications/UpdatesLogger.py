
import threading
import time
from typing import List
from plugin_utils.helpers import getLayerByName
from plugin_utils.traversal import traverseObj

from qgis.core import (QgsProject, QgsLayerTreeLayer,
                       QgsRasterLayer, QgsVectorLayer)

from qgis._core import Qgis, QgsProject, QgsLayerTreeLayer, QgsVectorLayer, QgsRasterLayer, QgsWkbTypes, QgsField, QgsFields

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, pyqtSignal, QTranslator, QRect, QObject
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget, QPushButton
from specklepy.logging import metrics
from specklepy.api.credentials import Account
from specklepy.api.models import Stream, Branch, Commit 
from specklepy.objects import Base

from specklepy.logging.exceptions import SpeckleException 
from specklepy.api.wrapper import StreamWrapper

import inspect
from speckle.converter.layers.feature import updateFeat
from speckle.notifications.utils import TABLE_ATTRS

from ui.logger import logToUser
from ui.validation import tryGetBranch, tryGetObject

class UpdatesLogger(QWidget):
    
    sendUpdate = pyqtSignal(str, str, str, str) #branch, commit, user, url

    # constructor
    def __init__(self, parent=None):
        super(UpdatesLogger, self).__init__(parent)

        self.parentWidget = parent       
        self.layout = QVBoxLayout(self)
        self.setGeometry(0, 0, 0, 0)

        dataStorage = self.parentWidget.dataStorage

        t = threading.Thread(target=self.runChecks, args=(dataStorage,))
        t.start()

    def runChecks(self, dataStorage):
        while True:
            if dataStorage.runUpdates == False: 
                return
            time.sleep(10)
            #print("check")
            try:
                table = self.findDashboardTable(dataStorage)
                if table is None: continue
                
                #for url, uuid, commit_id in dataStorage.streamsToFollow:
                for f in table.getFeatures():
                    #url = "https://speckle.xyz/streams/17b0b76d13/branches/random_tests"
                    url = f["Branch URL"]
                    if isinstance(url, str):
                        url = url.split(" ")[0].split("?")[0].split("&")[0]
                        commit_id = f["commit_id"]

                        try: 
                            branch = tryGetBranch(url)
                            if isinstance(branch, Branch):
                                try:
                                    latest_commit_id = branch.commits.items[0].id
                                    if latest_commit_id != commit_id:
                                        url_commit= url.split("branches")[0] + "commits/" + latest_commit_id
                                        self.parentWidget.updLog.sendUpdate.emit(branch.name, latest_commit_id, branch.commits.items[0].authorName, url_commit)
                                except Exception as e:
                                    logToUser(e, level = 1, func = inspect.stack()[0][3])
                                    self.runChecks(dataStorage)
                        except Exception as e:
                            logToUser(e, level = 1, func = inspect.stack()[0][3])
                            self.runChecks(dataStorage)
            except Exception as e:
                logToUser(e, level = 1, func = inspect.stack()[0][3])
                self.runChecks(dataStorage)
    
    def findDashboardTable(self, dataStorage):
        
        newLayerName = "Speckle_dashboard"
        root = dataStorage.project.layerTreeRoot()
        new_layer = None

        found = 0
        for child in root.children():
            if isinstance(child, QgsLayerTreeLayer): 
                if child.name() == newLayerName:
                    found +=1
                    new_layer = child.layer()
                    return new_layer

        if found == 0:
            return None 
        
    def addUpdate(self, dockwidget, branch_name: str, latest_commit_id: str, user: str, url_commit: str):

        layer = getLayerByName(dockwidget.dataStorage.project, "Speckle_dashboard")

        #for i, tup in enumerate(self.dataStorage.streamsToFollow):
        for i, f in enumerate(layer.getFeatures()):
            #(url, uuid, commit_id) = tup
            url = f["Branch URL"].split(" ")[0].split("?")[0].split("&")[0]
            sw = StreamWrapper(url)
            commit_id = f["commit_id"]
            branch = tryGetBranch(url)
            if branch_name == branch.name:
                if commit_id is not None:
                    logToUser(f"Branch \"{branch_name}\" was updated by \"{user}\"", level=0, url = url_commit, plugin=dockwidget)
                
                self.addTraverseProps(sw, layer, f, url, branch.commits.items[0].referencedObject)

                # overwrite 
                layer.startEditing()
                f["Branch URL"] = url
                f["commit_id"] = latest_commit_id
                layer.updateFeature(f)
                layer.commitChanges()

        return
    
    def addTraverseProps(self, sw, layer, f, url, ref_id):
        obj: Base = tryGetObject(url, ref_id)

        layer.startEditing()
        updated_f: dict = traverseObj(sw = sw, base = obj, attrs = TABLE_ATTRS)
        for i, (key,value) in enumerate(updated_f.items()):
            f[key] = value

        layer.updateFeature(f)
        layer.commitChanges()