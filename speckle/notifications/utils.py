from qgis.core import (QgsProject, QgsLayerTreeLayer, QgsFeature,
                       QgsRasterLayer, QgsVectorLayer)

from qgis._core import Qgis, QgsProject, QgsLayerTreeLayer, QgsVectorLayer, QgsRasterLayer, QgsWkbTypes, QgsField, QgsFields

from PyQt5.QtCore import QVariant, QDate, QDateTime

from ui.validation import tryGetStream
from specklepy.api.wrapper import StreamWrapper

TABLE_ATTRS = [
               ("area_residential",QVariant.Double,0),
               ("area_office",QVariant.Double,0),
               ("area_commercial",QVariant.Double,0),
               ("area_natural",QVariant.Double,0),
               ("custom_land_use",QVariant.String,[])
               ]

def addDashboardTable(project):
    #EXPERIMENTAL - add a table for a Dashboard
    newLayerName = "Speckle_dashboard"
    root = project.layerTreeRoot()
    new_layer = None

    found = 0
    for child in root.children():
        if isinstance(child, QgsLayerTreeLayer): 
            if child.name() == newLayerName:
                found +=1
                new_layer = child.layer()
                addDashboardField(new_layer)
                break

    if found == 0:
        #layerGroup = root.insertGroup(0,newGroupName) #root.addChildNode(layerGroup)
        new_layer = QgsVectorLayer('None', newLayerName, 'memory')
        addDashboardField(new_layer)
        addBranchFeatures(new_layer)
        project.instance().addMapLayer(new_layer)

def addDashboardField(layer):

    field_names = [field.name() for field in layer.fields()]
    if "Branch URL" not in field_names:
        fields = QgsFields()
        fields.append(QgsField("Branch URL", QVariant.String))
        fields.append(QgsField("commit_id", QVariant.String))
        addTableAttrs(layer)

        pr = layer.dataProvider()
        layer.startEditing()

        pr.addAttributes(fields)

        layer.updateFields()
        layer.commitChanges()

def addBranchFeatures(layer):
    fets = []
    stream_url = "https://speckle.xyz/streams/62973cd221"
    sw = StreamWrapper(stream_url)
    stream = tryGetStream(sw)
    for branch in stream.branches.items:
        url = stream_url + "/branches/" + branch.name
        feat = QgsFeature()
        feat.setFields(layer.fields()) 
        feat["Branch URL"] = url 
        fets.append(feat)
    
    layer.startEditing()
    pr = layer.dataProvider()
    pr.addFeatures(fets)
    layer.commitChanges()

def addTableAttrs(layer):
    
    pr = layer.dataProvider()
    layer.startEditing()
    fields = QgsFields()

    for attr in TABLE_ATTRS:
        fields.append(QgsField(attr[0], attr[1]))

    pr.addAttributes(fields)

    layer.updateFields()
    layer.commitChanges()
