"""
Contains all Layer related classes and methods.
"""
from typing import List, Union

from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)
from qgis.core import (Qgis, QgsRasterLayer,
                       QgsVectorLayer, QgsProject, QgsLayerTree, QgsLayerTreeNode, QgsCoordinateReferenceSystem)
from speckle.converter.geometry.point import pointToNative
from speckle.converter.layers.CRS import CRS
from speckle.converter.layers.Layer import Layer
from speckle.converter.layers.feature import featureToSpeckle, rasterFeatureToSpeckle, featureToNative
from speckle.converter.layers.utils import getLayerGeomType, getVariantFromValue, getLayerAttributes
from speckle.logging import logger
from specklepy.objects import Base

import numpy as np


def getLayers(tree: QgsLayerTree, parent: QgsLayerTreeNode) -> List[QgsLayerTreeNode]:
    """Gets a list of all layers in the given QgsLayerTree"""

    children = parent.children()
    layers = []
    for node in children:
        if tree.isLayer(node):
            layers.append(node)
            continue
        if tree.isGroup(node):
            layers.extend(getLayers(tree, node))
    return layers


def convertSelectedLayers(layers, selectedLayerNames, projectCRS, project):
    """Converts the current selected layers to Speckle"""
    result = []
    for layer in layers:
        if layer.name() in selectedLayerNames:
            result.append(layerToSpeckle(layer, projectCRS, project))
    return result


def layerToSpeckle(layer, projectCRS, project): #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    layerName = layer.name()
    selectedLayer = layer.layer()
    crs = selectedLayer.crs()
    units = "m"
    if crs.isGeographic(): units = "m" ## specklepy.logging.exceptions.SpeckleException: SpeckleException: Could not understand what unit degrees is referring to. Please enter a valid unit (eg ['mm', 'cm', 'm', 'in', 'ft', 'yd', 'mi']). 
    layerObjs = []
    # Convert CRS to speckle, use the projectCRS
    speckleReprojectedCrs = CRS(name=projectCRS.authid(), wkt=projectCRS.toWkt(), units=units) 

    if isinstance(selectedLayer, QgsVectorLayer):

        fieldnames = [field.name() for field in selectedLayer.fields()]

        # write feature attributes
        for f in selectedLayer.getFeatures():
            b = featureToSpeckle(fieldnames, f, crs, projectCRS, project, selectedLayer)
            layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleReprojectedCrs, layerObjs, "VectorLayer", getLayerGeomType(selectedLayer))
        layerBase.applicationId = selectedLayer.id()
        return layerBase

    if isinstance(selectedLayer, QgsRasterLayer):
        # write feature attributes
        b = rasterFeatureToSpeckle(selectedLayer, projectCRS, project)
        layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleReprojectedCrs, layerObjs, "RasterLayer")
        layerBase.applicationId = selectedLayer.id()
        return layerBase


def receiveRaster(project, source_folder, name, epsg, rasterDimensions, bands, rasterBandVals, pt, rasterResXY): 
    ## https://opensourceoptions.com/blog/pyqgis-create-raster/
    # creating file in temporary folder: https://stackoverflow.com/questions/56038742/creating-in-memory-qgsrasterlayer-from-the-rasterization-of-a-qgsvectorlayer-wit
    #print(source_folder)
    fn = source_folder + '/' + name + '.tif' #'_received_raster.tif'
    #print(fn)

    driver = gdal.GetDriverByName('GTiff')
    # create raster dataset
    ds = driver.Create(fn, xsize=rasterDimensions[0], ysize=rasterDimensions[1], bands=bands, eType=gdal.GDT_Float32)

    # Write data to raster band
    for i in range(bands):
        rasterband = np.array(rasterBandVals[i])
        rasterband = np.reshape(rasterband,(rasterDimensions[1], rasterDimensions[0]))
        ds.GetRasterBand(i+1).WriteArray(rasterband) # or "rasterband.T"

    # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
    ds.SetGeoTransform([pt.x(), rasterResXY[0], 0, pt.y(), 0, rasterResXY[1]])
    # create a spatial reference object
    srs = osr.SpatialReference()
    #  For the Universal Transverse Mercator the SetUTM(Zone, North=1 or South=2)
    srs.ImportFromEPSG(epsg) # from https://gis.stackexchange.com/questions/34082/creating-raster-layer-from-numpy-array-using-pyqgis
    ds.SetProjection(srs.ExportToWkt())
    # close the rater datasource by setting it equal to None
    ds = None
    raster_layer = QgsRasterLayer(fn, name, 'gdal')
    project.addMapLayer(raster_layer)
    return raster_layer


def layerToNative(layer: Layer, streamId: str) -> Union[QgsVectorLayer, QgsRasterLayer, None]:
    layerType = type(layer.type)
    if layer.type is None:
        # Handle this case
        return
    elif layer.type.endswith("VectorLayer"):
        return vectorLayerToNative(layer, streamId)
    elif layer.type.endswith("RasterLayer"):
        return rasterLayerToNative(layer, streamId)
    return None

def nonQgisToNative(layerContentList:Base, layerName: str, streamId: str) -> Union[QgsVectorLayer, QgsRasterLayer, None]:
    #layerType = QgsVectorLayer
    #if layer.type is None:
    #    # Handle this case
    #    return
    print(layerContentList)
    #TODO: filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
    recreateVectorLayer(layerContentList)
    return None

def recreateVectorLayer(layerContentList): 
    #TODO get Project CRS, use it by default for the new received layer
    return

def vectorLayerToNative(layer: Layer, streamId: str):
    vl = None
    crs = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt) #moved up, because CRS of existing layer needs to be rewritten

    #TODO CREATE A GROUP "received blabla" with sublayers
    newName = f'{streamId}_latest_{layer.name}'
    for lyr in QgsProject.instance().mapLayers().values(): 
        #print(lyr.name())
        if lyr.name() == newName: #lyr.id() == layer.applicationId: # dangerous, because it rewrites the source file on the disk  ###### check by unique name
            vl = lyr
            vl.startEditing()
            for feat in vl.getFeatures():
                vl.deleteFeature(feat.id())
            #fets = [featureToNative(feature) for feature in layer.features if featureToNative(feature) != ""]
            fets = []
            for f in layer.features: 
                new_feat = featureToNative(f)
                if new_feat != "": fets.append(new_feat)
            #list(filter(lambda a: a !="", fets))
            pr = vl.dataProvider()
            pr.addFeatures(fets)
            vl.setCrs(crs)
            vl.updateExtents()
            vl.commitChanges()
            return vl
    if vl is None:
        crsid = crs.authid()
        #print(layer.geomType)
        vl = QgsVectorLayer(layer.geomType+"?crs="+crsid, newName, "memory") # do something to distinguish: stream_id_latest_name
        QgsProject.instance().addMapLayer(vl)

        pr = vl.dataProvider()
        vl.startEditing()
        vl.setCrs(crs)
        attrs = getLayerAttributes(layer)
        pr.addAttributes(attrs)
        vl.updateFields()
        
        fets = []
        for f in layer.features: 
            new_feat = featureToNative(f)
            if new_feat != "": 
                fets.append(new_feat)

        pr = vl.dataProvider()
        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()
        return vl


def rasterLayerToNative(layer: Layer, streamId: str):
        # testing, only for receiving layers
    source_folder = QgsProject.instance().absolutePath()

    if(source_folder == ""):
        logger.logToUser(f"Raster layers can only be received on an existing saved project. Layer {layer.name} will be ignored", Qgis.Warning)
        return None

    project = QgsProject.instance()
    projectCRS = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    epsg = int(str(projectCRS).split(":")[len(str(projectCRS).split(":"))-1].split(">")[0])
    
    feat = layer.features[0]
    bandNames = feat["Band names"]
    bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

    newName = f'{streamId}_latest_{layer.name}'
    receiveRaster(project, source_folder, newName, epsg, [feat["X pixels"],feat["Y pixels"]],  feat["Band count"], bandValues, pointToNative(feat["displayValue"][0]), [feat["X resolution"],feat["Y resolution"]])
    
    return None


'''
def reprojectLayer(layer, targetCRS, project):

    if isinstance(layer.layer(), QgsVectorLayer):
        ### create copy of the layer in memory
        typeGeom = QgsWkbTypes.displayString(int(layer.layer().wkbType())) #returns e.g. Point, Polygon, Line
        crsId = layer.layer().crs().authid()
        layerReprojected = QgsVectorLayer(typeGeom+"?crs="+crsId, layer.name() + "_copy", "memory")

        ### copy fields/attributes to the new layer
        fields = layer.layer().dataProvider().fields().toList()
        layerReprojected.dataProvider().addAttributes(fields)
        layerReprojected.updateFields()

        ### get and transform the features
        features=[f for f in layer.layer().getFeatures()]
        xform = QgsCoordinateTransform(layer.layer().crs(), targetCRS, project)
        for feature in features:
            geometry = feature.geometry()
            geometry.transform(xform)
            feature.setGeometry(geometry)

        layerReprojected.dataProvider().addFeatures(features)
        layerReprojected.setCrs(targetCRS)

        return layerReprojected

    else:
        return layer.layer()
'''
