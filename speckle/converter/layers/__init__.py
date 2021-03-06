"""
Contains all Layer related classes and methods.
"""
from typing import List, Union

from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)
from qgis._core import Qgis, QgsVectorLayer, QgsWkbTypes, QgsField
from qgis.core import (Qgis, QgsRasterLayer,
                       QgsVectorLayer, QgsProject, 
                       QgsLayerTree, QgsLayerTreeGroup, QgsLayerTreeNode, 
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsFields, QgsRenderContext, QgsLayout, 
                       QgsFeatureRenderer, QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
                       QgsLineSymbol, QgsGraduatedSymbolRenderer, QgsRendererCategory,
                       QgsGradientColorRamp, QgsRendererRange, QgsSymbol, QgsSymbolLayer, 
                       QgsApplication,QgsSymbolLayerRegistry, )
from speckle.converter.geometry.point import pointToNative
from speckle.converter.layers.CRS import CRS
from speckle.converter.layers.Layer import Layer, RasterLayer
from speckle.converter.layers.feature import featureToSpeckle, rasterFeatureToSpeckle, featureToNative, cadFeatureToNative
from speckle.converter.layers.utils import getLayerGeomType, getVariantFromValue, getLayerAttributes
from speckle.logging import logger
from specklepy.objects import Base

from speckle.converter.layers.symbology import vectorRendererToNative, rasterRendererToNative, rendererToSpeckle

from PyQt5.QtGui import QColor

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
    layerCRS = CRS(name=crs.authid(), wkt=crs.toWkt(), units=units) 
    
    renderer = selectedLayer.renderer()
    layerRenderer = rendererToSpeckle(renderer) 
    
    if isinstance(selectedLayer, QgsVectorLayer):

        fieldnames = [field.name() for field in selectedLayer.fields()]

        # write feature attributes
        for f in selectedLayer.getFeatures():
            b = featureToSpeckle(fieldnames, f, crs, projectCRS, project, selectedLayer)
            layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(name=layerName, crs=speckleReprojectedCrs, features=layerObjs, type="VectorLayer", geomType=getLayerGeomType(selectedLayer))
        layerBase.type="VectorLayer"
        layerBase.renderer = layerRenderer
        layerBase.applicationId = selectedLayer.id()

        return layerBase

    if isinstance(selectedLayer, QgsRasterLayer):
        # write feature attributes
        b = rasterFeatureToSpeckle(selectedLayer, projectCRS, project)
        layerObjs.append(b)
        # Convert layer to speckle
        layerBase = RasterLayer(name=layerName, crs=speckleReprojectedCrs, rasterCrs=layerCRS, features=layerObjs, type="RasterLayer")
        layerBase.type="RasterLayer"
        layerBase.renderer = layerRenderer
        layerBase.applicationId = selectedLayer.id()
        return layerBase


def layerToNative(layer: Union[Layer, RasterLayer], streamBranch: str) -> Union[QgsVectorLayer, QgsRasterLayer, None]:

    if layer.type is None:
        # Handle this case
        return
    elif layer.type.endswith("VectorLayer"):
        return vectorLayerToNative(layer, streamBranch)
    elif layer.type.endswith("RasterLayer"):
        return rasterLayerToNative(layer, streamBranch)
    return None

def cadLayerToNative(layerContentList:Base, layerName: str, streamBranch: str) -> Union[QgsVectorLayer, QgsRasterLayer, None]:

    geom_points = []
    geom_polylines = []
    geom_polygones = []
    geom_meshes = []
    #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
    for geom in layerContentList:
        #print(geom)
        if geom.speckle_type == "Objects.Geometry.Point": 
            geom_points.append(geom)
        if geom.speckle_type == "Objects.Geometry.Line" or geom.speckle_type == "Objects.Geometry.Polyline" or geom.speckle_type == "Objects.Geometry.Curve" or geom.speckle_type == "Objects.Geometry.Arc" or geom.speckle_type == "Objects.Geometry.Circle" or geom.speckle_type == "Objects.Geometry.Polycurve":
            geom_polylines.append(geom)
    
    if len(geom_points)>0: layer_points = cadVectorLayerToNative(geom_points, layerName, "Points", streamBranch)
    if len(geom_polylines)>0: layer_polylines = cadVectorLayerToNative(geom_polylines, layerName, "Polylines", streamBranch)

    return [layer_points, layer_polylines]

def cadVectorLayerToNative(geomList, layerName: str, geomType: str, streamBranch: str): 
    #get Project CRS, use it by default for the new received layer
    vl = None
    layerName = layerName + "/" + geomType
    crs = QgsProject.instance().crs() #QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    if crs.isGeographic is True: 
        logger.logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", Qgis.Warning)

    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName) # -> QgsLayerTreeNode
    else:
        root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch}_{layerName}'
    #childId = None
    #for child in layerGroup.children(): 
    #    QgsProject.instance().removeMapLayer(child.layerId())
        #if child.name() == newName: 
        #    childId = child.layerId()
         #   break
    
    # modify existing layer (if exists) 
    #if QgsProject.instance().mapLayer(childId) is not None:
    #    vl = QgsProject.instance().removeMapLayer(childId)
    #    vl = None

    #or create one from scratch
    crsid = crs.authid()
    if geomType == "Points": geomType = "PointZ"
    elif geomType == "Polylines": geomType = "LineStringZ"
    vl = QgsVectorLayer( geomType +"?crs="+crsid, newName, "memory") # do something to distinguish: stream_id_latest_name
    QgsProject.instance().addMapLayer(vl, False)

    pr = vl.dataProvider()
    vl.startEditing()
    vl.setCrs(crs)
    
    # create list of Features (fets) and list of Layer fields (fields)
    attrs = QgsFields()
    fets = []
    fetIds = []
    fetColors = []
    for f in geomList[:]: 
        new_feat, newFields = cadFeatureToNative(f, attrs, newName)
        # update attrs for the next feature (if more fields were added from previous feature)
        
        if new_feat != "": 
            fets.append(new_feat)
            for a in newFields.toList(): 
                #if a not in attrs.toList(): 
                attrs.append(a) 
            
            pr.addAttributes(newFields) # add new attributes from the current object
            fetIds.append(f.id)
            try: fetColors.append(f.displayStyle.color) #, print(str(f.id)+ ': ' + str(f.displayStyle.color))
            except: fetColors.append(None)
        #else: geomList.remove(f)
    
    # add Layer attribute fields
    pr.addAttributes(newFields)
    vl.updateFields()

    #pr = vl.dataProvider()
    pr.addFeatures(fets)
    vl.updateExtents()
    vl.commitChanges()
    layerGroup.addLayer(vl)

    ################################### RENDERER ###########################################
    # only set up renderer if the layer is just created
    attribute = '_Speckle_ID'
    categories = []
    for i in range(len(fets)):
        rgb = fetColors[i]
        if rgb:
            r = (rgb & 0xFF0000) >> 16
            g = (rgb & 0xFF00) >> 8
            b = rgb & 0xFF 
            color = QColor.fromRgb(r, g, b)
        else: color = QColor.fromRgb(0,0,0)

        symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
        symbol.setColor(color)
        categories.append(QgsRendererCategory(fetIds[i], symbol, fetIds[i], True) )  
    # create empty category for all other values
    symbol2 = symbol.clone()
    symbol2.setColor(QColor.fromRgb(0,0,0))
    cat = QgsRendererCategory()
    cat.setSymbol(symbol2)
    cat.setLabel('Other')
    categories.append(cat)        
    rendererNew = QgsCategorizedSymbolRenderer(attribute, categories)

    try: vl.setRenderer(rendererNew)
    except: pass

    return vl

def vectorLayerToNative(layer: Layer, streamBranch: str):
    vl = None
    crs = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt) #moved up, because CRS of existing layer needs to be rewritten

    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)
    else:
        root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch}/{layer.name}'
    #childId = None
    #for child in layerGroup.children(): 
    #    QgsProject.instance().removeMapLayer(child.layerId())
        #if child.name() == newName: 
        #    childId = child.layerId()
        #    break
    
    #in QGIS panel: 
    '''
root = QgsProject.instance().layerTreeRoot()
print(root.layerOrder())
layer = root.layerOrder()[0]
cats = layer.renderer().categories()
[print(str(i.label()) + ': ' + str(i.value())) for i in cats]   
    '''
    # delete existing layer (if exists) 
    #if QgsProject.instance().mapLayer(childId) is not None:
    #    vl = QgsProject.instance().removeMapLayer(childId)
    #    vl = None
    #or create one from scratch
    crsid = crs.authid()
    vl = QgsVectorLayer(layer.geomType+"?crs="+crsid, newName, "memory") # do something to distinguish: stream_id_latest_name
    QgsProject.instance().addMapLayer(vl, False)

    pr = vl.dataProvider()
    vl.startEditing()
    vl.setCrs(crs)
    #vl.updateFields()

    attrs = getLayerAttributes(layer)
    #pr.addAttributes(attrs)
    vl.updateFields()
    
    fets = []
    for f in layer.features: 
        new_feat, newFields = featureToNative(f, attrs)
        if new_feat != "": fets.append(new_feat)

    # add Layer attribute fields
    pr.addAttributes(newFields)
    vl.updateFields()
    
    #print(pr.get
    #pr = vl.dataProvider()
    pr.addFeatures(fets)
    vl.updateExtents()
    vl.commitChanges()
    layerGroup.addLayer(vl)

    rendererNew = vectorRendererToNative(layer)

    try: vl.setRenderer(rendererNew)
    except: pass
    
    return vl

def rasterLayerToNative(layer: RasterLayer, streamBranch: str):

    vl = None
    crs = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt) #moved up, because CRS of existing layer needs to be rewritten
    # try, in case of older version "rasterCrs" will not exist 
    try: crsRaster = QgsCoordinateReferenceSystem.fromWkt(layer.rasterCrs.wkt) #moved up, because CRS of existing layer needs to be rewritten
    except: 
        crsRaster = crs
        logger.logToUser(f"Raster layer might have been sent from the older version of plugin. Try sending it again for more accurate results.", Qgis.Warning)
    

    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)
    else:
        root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch}/{layer.name}'
    #childId = None
    #for child in layerGroup.children(): 
    #    if child.name() == newName: 
    #        childId = child.layerId()
    #        break
    # modify existing layer (if exists) 
    #if QgsProject.instance().mapLayer(childId) is not None:
    #    #existingRaster = QgsProject.instance().mapLayer(childId)
    #    QgsProject.instance().removeMapLayer(childId)

    

    ######################## testing, only for receiving layers #################
    source_folder = QgsProject.instance().absolutePath()

    if(source_folder == ""):
        logger.logToUser(f"Raster layers can only be received in an existing saved project. Layer {layer.name} will be ignored", Qgis.Warning)
        return None

    project = QgsProject.instance()
    projectCRS = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    crsid = crsRaster.authid()
    try: epsg = int(crsid.split(":")[1]) 
    except: 
        epsg = int(str(projectCRS).split(":")[len(str(projectCRS).split(":"))-1].split(">")[0])
        logger.logToUser(f"CRS of the received raster cannot be identified. Project CRS will be used.", Qgis.Warning)
    
    feat = layer.features[0]
    bandNames = feat["Band names"]
    bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

    #newName = f'{streamBranch}_latest_{layer.name}'

    ###########################################################################

    ## https://opensourceoptions.com/blog/pyqgis-create-raster/
    # creating file in temporary folder: https://stackoverflow.com/questions/56038742/creating-in-memory-qgsrasterlayer-from-the-rasterization-of-a-qgsvectorlayer-wit

    fn = source_folder + '/' + newName.replace("/","_") + '.tif' #'_received_raster.tif'
    driver = gdal.GetDriverByName('GTiff')
    # create raster dataset
    ds = driver.Create(fn, xsize=feat["X pixels"], ysize=feat["Y pixels"], bands=feat["Band count"], eType=gdal.GDT_Float32)

    # Write data to raster band
    for i in range(feat["Band count"]):
        rasterband = np.array(bandValues[i])
        rasterband = np.reshape(rasterband,(feat["Y pixels"], feat["X pixels"]))
        ds.GetRasterBand(i+1).WriteArray(rasterband) # or "rasterband.T"

    # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
    pt = pointToNative(feat["displayValue"][0])
    xform = QgsCoordinateTransform(crs, crsRaster, project)
    pt.transform(xform)
    ds.SetGeoTransform([pt.x(), feat["X resolution"], 0, pt.y(), 0, feat["Y resolution"]])
    # create a spatial reference object
    srs = osr.SpatialReference()
    #  For the Universal Transverse Mercator the SetUTM(Zone, North=1 or South=2)
    srs.ImportFromEPSG(epsg) # from https://gis.stackexchange.com/questions/34082/creating-raster-layer-from-numpy-array-using-pyqgis
    ds.SetProjection(srs.ExportToWkt())
    # close the rater datasource by setting it equal to None
    ds = None

    raster_layer = QgsRasterLayer(fn, newName, 'gdal')
    QgsProject.instance().addMapLayer(raster_layer, False)
    layerGroup.addLayer(raster_layer)

    dataProvider = raster_layer.dataProvider()
    rendererNew = rasterRendererToNative(layer, dataProvider)

    try: raster_layer.setRenderer(rendererNew)
    except: pass

    return raster_layer
