
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
#from specklepy.logging import metrics
from specklepy.api.credentials import Account
from specklepy.api.models import Stream, Branch, Commit 
from specklepy.objects import Base

from specklepy.logging.exceptions import SpeckleException 
from specklepy.api.wrapper import StreamWrapper

import inspect
from speckle.converter.layers.feature import updateFeat
from speckle.notifications.SpeckleDashboard import SpeckleDashboard
from speckle.notifications.utils import TABLE_ATTRS, addDashboardTable

from ui.logger import logToUser
from ui.validation import tryGetBranch, tryGetObject

class UpdatesLogger(QWidget):
    
    sendUpdate = pyqtSignal(str, str, str, str) #branch, commit, user, url
    dashboard = None
    iface = None
    dataStorage = None
    cache: List[str] = []

    # constructor
    def __init__(self, parent=None):
        super(UpdatesLogger, self).__init__(parent)

        self.parentWidget = parent       
        self.layout = QVBoxLayout(self)
        self.setGeometry(0, 0, 0, 0)

        self.dataStorage = self.parentWidget.dataStorage
        self.iface = self.parentWidget.iface 
        
        #t = threading.Thread(target=self.runChecks, args=())
        #t.start()

    def runChecks(self):
        while True:
            if self.dataStorage.runUpdates == False: 
                return
            time.sleep(5)
            #print("check")
            try:
                table = self.findDashboardTable()
                if table is None: continue
                
                #for url, uuid, commit_id in dataStorage.streamsToFollow:
                for f in table.getFeatures():
                    #url = "https://speckle.xyz/streams/17b0b76d13/branches/random_tests"
                    url = f["Branch URL"]
                    if isinstance(url, str):
                        url = url.split("?")[0].split("&")[0]
                        commit_id = f["commit_id"]

                        try: 
                            branch = tryGetBranch(url)
                            if isinstance(branch, Branch):
                                try:
                                    try: latest_commit_id = branch.commits.items[0].id
                                    except: latest_commit_id = None 

                                    if latest_commit_id is not None and latest_commit_id != commit_id:
                                        url_commit= url.split("branches")[0] + "commits/" + latest_commit_id
                                        
                                        if latest_commit_id not in self.cache: # only show the update once
                                            self.parentWidget.updLog.sendUpdate.emit(branch.name, latest_commit_id, branch.commits.items[0].authorName, url_commit)
                                            self.cache.append(latest_commit_id)
                                except Exception as e:
                                    logToUser(e, level = 1, func = inspect.stack()[0][3])
                                    self.runChecks()
                        except Exception as e:
                            logToUser(e, level = 1, func = inspect.stack()[0][3])
                            self.runChecks()
            except Exception as e:
                logToUser(e, level = 1, func = inspect.stack()[0][3])
                self.runChecks()
    
    def findDashboardTable(self):
        
        newLayerName = "Speckle_dashboard"
        root = self.dataStorage.project.layerTreeRoot()
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
                
    def addUpdate(self): #, dockwidget, branch_name: str, latest_commit_id: str, user: str, url_commit: str):
        """Updata table layer properties"""
        layer = getLayerByName(self.dataStorage.project, "Speckle_dashboard")
        if layer is None:
            addDashboardTable(self.dataStorage.project)
            layer = getLayerByName(self.dataStorage.project, "Speckle_dashboard")

        for i, f in enumerate(layer.getFeatures()):
            #(url, uuid, commit_id) = tup
            url = f["Branch URL"].split("?")[0].split("&")[0]
            sw = StreamWrapper(url)
            commit_id = f["commit_id"]
            branch = tryGetBranch(url)

            # run only if commit changed
            try: latest_commit_id = branch.commits.items[0].id
            except: latest_commit_id = None 
            if f["updated"] == 0 or (latest_commit_id is not None and latest_commit_id != commit_id):
            
                try:
                    self.addTraverseProps(sw, layer, f, url, branch.commits.items[0].referencedObject)
                except: pass

                # overwrite 
                layer.startEditing()
                f["Branch URL"] = url
                f["commit_id"] = latest_commit_id
                f["updated"] = 1
                layer.updateFeature(f)
                layer.commitChanges()
                
            self.cache.clear()
        return

    def showDashboard(self): 
        if self.dashboard is None:
            self.dashboard = SpeckleDashboard()
            self.dashboard.dataStorage = self.dataStorage
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dashboard)
            self.dashboard.update()
            self.dashboard.show()
        else: 
            self.dashboard.update()
            self.dashboard.show()

    
    def addTraverseProps(self, sw, layer, f, url, ref_id):
        obj: Base = tryGetObject(url, ref_id)

        layer.startEditing()
        updated_f: dict = traverseObj(sw = sw, base = obj, attrs = TABLE_ATTRS)
        for i, (key,value) in enumerate(updated_f.items()):
            if isinstance(value, List): f[key] = str(value)
            else: f[key] = value

        layer.updateFeature(f)
        layer.commitChanges()
    