

from qgis.core import (QgsProject, QgsLayerTreeLayer,
                       QgsRasterLayer, QgsVectorLayer)

from qgis._core import Qgis, QgsProject, QgsLayerTreeLayer, QgsVectorLayer, QgsRasterLayer, QgsWkbTypes, QgsField, QgsFields

from PyQt5.QtCore import QVariant, QDate, QDateTime

from typing import List, Tuple, Union


class DataStorage:
    streamsToFollow: Union[List[Tuple[str, str, str]], None] = None #url, uuid, commitID
    project = None

    def __init__(self):
        print("hello")
        self.streamsToFollow = []
        self.streamsToFollow.append(("https://speckle.xyz/streams/17b0b76d13/branches/random_tests", "", "09a0f3e41a"))

    def addDashboardTable(self):
        #EXPERIMENTAL - add a table for a Dashboard
        newLayerName = "Speckle_dashboard"
        root = self.project.layerTreeRoot()
        new_layer = None

        found = 0
        for child in root.children():
            if isinstance(child, QgsLayerTreeLayer): 
                if child.name() == newLayerName:
                    found +=1
                    new_layer = child.layer()
                    self.addDashboardField(new_layer)
                    break

        if found == 0:
            #layerGroup = root.insertGroup(0,newGroupName) #root.addChildNode(layerGroup)
            new_layer = QgsVectorLayer('None', newLayerName, 'memory')
            self.addDashboardField(new_layer)
            self.project.instance().addMapLayer(new_layer)
    
    def addDashboardField(self, layer):

        field_names = [field.name() for field in layer.fields()]
        if "Branch URL" not in field_names:
            fields = QgsFields()
            fields.append(QgsField("Branch URL", QVariant.String))
            fields.append(QgsField("commit_id", QVariant.String))
            fields.append(QgsField("area", QVariant.Double))
            fields.append(QgsField("floors", QVariant.Double))

            pr = layer.dataProvider()
            layer.startEditing()

            pr.addAttributes(fields)

            layer.updateFields()
            layer.commitChanges()

