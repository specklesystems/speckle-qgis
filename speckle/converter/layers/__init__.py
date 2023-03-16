"""
Contains all Layer related classes and methods.
"""
import enum
import inspect
import math
from typing import List, Union
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh
import os
import time

from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)
from plugin_utils.helpers import findOrCreatePath, removeSpecialCharacters
#from qgis._core import Qgis, QgsVectorLayer, QgsWkbTypes
from qgis.core import (Qgis, QgsRasterLayer, 
                       QgsVectorLayer, QgsProject, QgsWkbTypes,
                       QgsLayerTree, QgsLayerTreeGroup, QgsLayerTreeNode, QgsLayerTreeLayer,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsFields, 
                       QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
                       QgsRendererCategory,
                       QgsSymbol)
from speckle.converter.geometry.point import pointToNative
from speckle.converter.layers.CRS import CRS
from speckle.converter.layers.Layer import VectorLayer, RasterLayer, Layer
from speckle.converter.layers.feature import featureToSpeckle, rasterFeatureToSpeckle, featureToNative, cadFeatureToNative, bimFeatureToNative 
from speckle.converter.layers.utils import colorFromRenderMaterial, getLayerGeomType, getLayerAttributes, saveCRS
from speckle.logging import logger
from speckle.converter.geometry.mesh import constructMesh, writeMeshToShp

from speckle.converter.layers.symbology import vectorRendererToNative, rasterRendererToNative, rendererToSpeckle

from PyQt5.QtGui import QColor
import numpy as np

from ui.logger import logToUser

GEOM_LINE_TYPES = ["Objects.Geometry.Line", "Objects.Geometry.Polyline", "Objects.Geometry.Curve", "Objects.Geometry.Arc", "Objects.Geometry.Circle", "Objects.Geometry.Ellipse", "Objects.Geometry.Polycurve"]


def getLayers(plugin, bySelection = False ) -> List[ Union[QgsLayerTreeLayer, QgsLayerTreeNode]]:
    """Gets a list of all layers in the given QgsLayerTree"""
    #print("___ get layers list ___")
    self = plugin.dockwidget
    layers = []
    if bySelection is True: # by selection 
        layers = plugin.iface.layerTreeView().selectedLayers()
    else: # from project data 
        project = QgsProject.instance()
        #all_layers_ids = [l.id() for l in project.mapLayers().values()]
        for item in plugin.current_layers:
            try: 
                id = item[1].id()
            except:
                logToUser(f'Saved layer not found: "{item[0]}"', level = 1, func = inspect.stack()[0][3])
                continue
            found = 0
            for l in project.mapLayers().values():
                if id == l.id():
                    layers.append(l)
                    found += 1
                    break 
            if found == 0: 
                logToUser(f'Saved layer not found: "{item[0]}"', level = 1, func = inspect.stack()[0][3])
    
    r'''
    children = parent.children()
    for node in children:
        #print(node)
        if tree.isLayer(node):
            #print(node)
            if isinstance(node.layer(), QgsVectorLayer) or isinstance(node.layer(), QgsRasterLayer): layers.append(node)
            continue
        if tree.isGroup(node):
            for lyr in getLayers(tree, node):
                if isinstance(lyr.layer(), QgsVectorLayer) or isinstance(lyr.layer(), QgsRasterLayer): layers.append(lyr) 
            #layers.extend( [ lyr for lyr in getLayers(tree, node) if isinstance(lyr.layer(), QgsVectorLayer) or isinstance(lyr.layer(), QgsRasterLayer) ] )
    '''
    return layers


def convertSelectedLayers(layers: List[Union[QgsVectorLayer, QgsRasterLayer]], selectedLayerIndex: List[int], selectedLayerNames: List[str], projectCRS: QgsCoordinateReferenceSystem, project: QgsProject) -> List[Union[VectorLayer, RasterLayer]]:
    """Converts the current selected layers to Speckle"""
    result = []

    for i, layer in enumerate(layers):
        result.append(layerToSpeckle(layer, projectCRS, project))
    
    return result


def layerToSpeckle(selectedLayer: Union[QgsVectorLayer, QgsRasterLayer], projectCRS: QgsCoordinateReferenceSystem, project: QgsProject) -> VectorLayer or RasterLayer: #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    layerName = selectedLayer.name()
    #except: layerName = layer.sourceName()
    #try: selectedLayer = selectedLayer.layer()
    #except: pass 
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

        fieldnames = [str(field.name()) for field in selectedLayer.fields()]

        # write feature attributes
        for f in selectedLayer.getFeatures():
            b = featureToSpeckle(fieldnames, f, crs, projectCRS, project, selectedLayer)
            layerObjs.append(b)
        # Convert layer to speckle
        layerBase = VectorLayer(units = "m", name=layerName, crs=speckleReprojectedCrs, features=layerObjs, type="VectorLayer", geomType=getLayerGeomType(selectedLayer))
        layerBase.type="VectorLayer"
        layerBase.renderer = layerRenderer
        layerBase.applicationId = selectedLayer.id()
        #print(layerBase.features)
        return layerBase

    if isinstance(selectedLayer, QgsRasterLayer):
        # write feature attributes
        b = rasterFeatureToSpeckle(selectedLayer, projectCRS, project)
        layerObjs.append(b)
        # Convert layer to speckle
        layerBase = RasterLayer(units = "m", name=layerName, crs=speckleReprojectedCrs, rasterCrs=layerCRS, features=layerObjs, type="RasterLayer")
        layerBase.type="RasterLayer"
        layerBase.renderer = layerRenderer
        layerBase.applicationId = selectedLayer.id()
        return layerBase


def layerToNative(layer: Union[Layer, VectorLayer, RasterLayer], streamBranch: str) -> Union[QgsVectorLayer, QgsRasterLayer, None]:

    if layer.type is None:
        # Handle this case
        return
    elif layer.type.endswith("VectorLayer"):
        return vectorLayerToNative(layer, streamBranch)
    elif layer.type.endswith("RasterLayer"):
        return rasterLayerToNative(layer, streamBranch)
    return None


def bimLayerToNative(layerContentList: List[Base], layerName: str, streamBranch: str):
    print("01______BIM layer to native")
    print(layerName)

    geom_meshes = []
    layer_meshes = None

    #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
    for geom in layerContentList:
        if geom.speckle_type =='Objects.Geometry.Mesh':
            geom_meshes.append(geom)
        else:
            try: 
                if geom.displayValue: geom_meshes.append(geom)
            except:
                try: 
                    if geom["@displayValue"]: geom_meshes.append(geom)
                except:
                    try: 
                        if geom.displayMesh: geom_meshes.append(geom)
                    except: pass
        
        #if geom.speckle_type == 'Objects.BuiltElements.Alignment':

    
    if len(geom_meshes)>0: layer_meshes = bimVectorLayerToNative(geom_meshes, layerName, "Mesh", streamBranch)

    return True

def bimVectorLayerToNative(geomList: List[Base], layerName_old: str, geomType: str, streamBranch: str): 
    print("02_________BIM vector layer to native_____")
    
    print(layerName_old)

    layerName = layerName_old.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")
    #layerName = removeSpecialCharacters(layerName_old)[:30]
    layerName = layerName[:50]
    print(layerName)

    #get Project CRS, use it by default for the new received layer
    vl = None
    layerName = layerName + "_" + geomType
    print(layerName)

    
    path = QgsProject.instance().absolutePath()
    if(path == ""):
        logToUser(f"BIM layers can only be received in an existing saved project. Layer {layerName} will be ignored", level = 1, func = inspect.stack()[0][3])
        return None

    path_bim = path + "/Layers_Speckle/BIM_layers/" + streamBranch+ "/" + layerName + "/" #arcpy.env.workspace + "\\" #

    findOrCreatePath(path_bim)
    print(path_bim)


    crs = QgsProject.instance().crs() #QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    #authid = saveCRS(crs, streamBranch)
    #time.sleep(0.01)

    if crs.isGeographic is True: 
        logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", level = 1, func = inspect.stack()[0][3])

    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName) # -> QgsLayerTreeNode
    else:
        layerGroup = root.insertGroup(0,newGroupName) #root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    #newName = f'{streamBranch}_{layerName}'
    
    newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'
    newName_shp = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{layerName}'

    if "mesh" in geomType.lower(): geomType = "MultiPolygonZ"

    #crsid = crs.authid()
    
    shp = writeMeshToShp(geomList, path_bim + newName_shp)
    if shp is None: return 
    print("____ meshes saved___")
    print(shp)

    
    
    vl_shp = QgsVectorLayer( shp + ".shp", newName, "ogr") # do something to distinguish: stream_id_latest_name
    vl = QgsVectorLayer( geomType+ "?crs=" + crs.authid(), newName, "memory") # do something to distinguish: stream_id_latest_name
    vl.setCrs(crs)
    QgsProject.instance().addMapLayer(vl, False)
    #try: 
    #    vl_shp.deleteAttributes(vl.fields()) #if DisplayMesh exists 
    #    vl_shp.commitChanges()
    #except: pass 
    #print(vl_shp.fields().names())

    pr = vl.dataProvider()
    vl.startEditing()
    #print(vl.crs())

    newFields = getLayerAttributes(geomList)
    print("___________Layer fields_____________")
    print(newFields.toList())

    # add Layer attribute fields
    pr.addAttributes(newFields)
    vl.updateFields()

    # create list of Features (fets) and list of Layer fields (fields)
    #attrs = QgsFields()
    fets = []
    fetIds = []
    fetColors = []
    
    for i,f in enumerate(geomList[:]): 
        try:
            exist_feat: None = None
            for n, shape in enumerate(vl_shp.getFeatures()):
                #print(shape["speckle_id"])
                if shape["speckle_id"] == f.id:
                    exist_feat = vl_shp.getFeature(n)
                    break
            if exist_feat is None: continue 

            new_feat = bimFeatureToNative(exist_feat, f, vl.fields(), crs, path_bim)
            if new_feat is not None and new_feat != "": 
                colorFound = 0
                try: # get render material from any part of the mesh (list of items in displayValue)
                    for k, item in enumerate(f.displayValue):
                        try:
                            fetColors.append(item.renderMaterial)  
                            colorFound += 1
                            break
                        except: pass
                except: 
                    try:
                        for k, item in enumerate(f["@displayValue"]):
                            try: 
                                fetColors.append(item.renderMaterial) 
                                colorFound += 1
                                break
                            except: pass
                    except: 
                        try:
                            fetColors.append(f.renderMaterial) 
                            colorFound += 1
                        except: pass
                fets.append(new_feat)
                vl.addFeature(new_feat)
                fetIds.append(f.id)
                if colorFound == 0: fetColors.append(None)
        except Exception as e: print(e)
    
    vl.updateExtents()
    vl.commitChanges()
    layerGroup.addLayer(vl)
    print(vl)

    
    try: 
        ################################### RENDERER 3D ###########################################
        #rend3d = QgsVectorLayer3DRenderer() # https://qgis.org/pyqgis/3.16/3d/QgsVectorLayer3DRenderer.html?highlight=layer3drenderer#module-QgsVectorLayer3DRenderer

        plugin_dir = os.path.dirname(__file__)
        renderer3d = os.path.join(plugin_dir, 'renderer3d.qml')
        print(renderer3d)

        vl.loadNamedStyle(renderer3d)
        vl.triggerRepaint()
    except: pass 
    
    try:
        ################################### RENDERER ###########################################
        # only set up renderer if the layer is just created
        attribute = 'Speckle_ID'
        categories = []
        for i in range(len(fets)):
            material = fetColors[i]
            color = colorFromRenderMaterial(material)

            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
            symbol.setColor(color)
            categories.append(QgsRendererCategory(fetIds[i], symbol, fetIds[i], True) )  
        # create empty category for all other values
        symbol2 = symbol.clone()
        symbol2.setColor(QColor.fromRgb(245,245,245))
        cat = QgsRendererCategory()
        cat.setSymbol(symbol2)
        cat.setLabel('Other')
        categories.append(cat)        
        rendererNew = QgsCategorizedSymbolRenderer(attribute, categories)
    except Exception as e: print(e)

    try: vl.setRenderer(rendererNew)
    except: pass

    return vl

def cadLayerToNative(layerContentList:Base, layerName: str, streamBranch: str) -> List[QgsVectorLayer or None]:
    print("02_________ CAD vector layer to native_____")
    geom_points = []
    geom_polylines = []
    geom_meshes = []

    layer_points = None
    layer_polylines = None
    #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
    for geom in layerContentList:
        #print(geom)
        if geom.speckle_type == "Objects.Geometry.Point": 
            geom_points.append(geom)
        if geom.speckle_type == "Objects.Geometry.Line" or geom.speckle_type == "Objects.Geometry.Polyline" or geom.speckle_type == "Objects.Geometry.Curve" or geom.speckle_type == "Objects.Geometry.Arc" or geom.speckle_type == "Objects.Geometry.Circle" or geom.speckle_type == "Objects.Geometry.Ellipse" or geom.speckle_type == "Objects.Geometry.Polycurve":
            geom_polylines.append(geom)
        try:
            if geom.speckle_type.endswith(".ModelCurve") and geom["baseCurve"].speckle_type in GEOM_LINE_TYPES:
                geom_polylines.append(geom["baseCurve"])
        except: pass
    
    if len(geom_points)>0: layer_points = cadVectorLayerToNative(geom_points, layerName, "Points", streamBranch)
    if len(geom_polylines)>0: layer_polylines = cadVectorLayerToNative(geom_polylines, layerName, "Polylines", streamBranch)
    #print(layerName)
    #print(layer_points)
    #print(layer_polylines)
    return [layer_points, layer_polylines]

def cadVectorLayerToNative(geomList: List[Base], layerName: str, geomType: str, streamBranch: str) -> QgsVectorLayer: 
    print("___________cadVectorLayerToNative")
    #get Project CRS, use it by default for the new received layer
    vl = None
    layerName = layerName + "/" + geomType
    print(layerName)
    crs = QgsProject.instance().crs() #QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    #authid = saveCRS(crs, streamBranch)
    #time.sleep(0.01)

    if crs.isGeographic is True: 
        logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", level = 1, func = inspect.stack()[0][3])

    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName) # -> QgsLayerTreeNode
    else:
        layerGroup = root.insertGroup(0,newGroupName) #root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    #newName = f'{streamBranch}_{layerName}'
    newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{layerName}'


    #or create one from scratch
    #crsid = crs.authid()
    if geomType == "Points": geomType = "PointZ"
    elif geomType == "Polylines": geomType = "LineStringZ"
    vl = QgsVectorLayer( geomType+ "?crs=" + crs.authid() , newName, "memory") # do something to distinguish: stream_id_latest_name
    vl.setCrs(crs)
    QgsProject.instance().addMapLayer(vl, False)

    pr = vl.dataProvider()
    vl.startEditing()
    #print(vl.crs())

    newFields = getLayerAttributes(geomList)
    print(newFields.toList())
    print(geomList)
    
    # create list of Features (fets) and list of Layer fields (fields)
    attrs = QgsFields()
    fets = []
    fetIds = []
    fetColors = []
    for f in geomList[:]: 
        new_feat = cadFeatureToNative(f, newFields)
        # update attrs for the next feature (if more fields were added from previous feature)

        print("________cad feature to add")
        #print(new_feat)
        if new_feat is not None and new_feat != "": 
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
    print(vl)

    ################################### RENDERER ###########################################
    # only set up renderer if the layer is just created
    attribute = 'Speckle_ID'
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

def vectorLayerToNative(layer: Layer or VectorLayer, streamBranch: str):
    vl = None
    crs = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt) #moved up, because CRS of existing layer needs to be rewritten
    authid = saveCRS(crs, streamBranch)
    time.sleep(0.01)

    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)
    else:
        layerGroup = root.insertGroup(0,newGroupName)
        #root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{layer.name}'

    # particularly if the layer comes from ArcGIS
    geomType = layer.geomType # for ArcGIS: Polygon, Point, Polyline, Multipoint, MultiPatch
    if geomType =="Point": geomType = "Point"
    elif geomType =="Polygon": geomType = "Multipolygon"
    elif geomType =="Polyline": geomType = "MultiLineString"
    elif geomType =="Multipoint": geomType = "Point"
    
    #crsid = crs.authid()
    vl = QgsVectorLayer(geomType+ "?crs=" + authid, newName, "memory") # do something to distinguish: stream_id_latest_name
    vl.setCrs(crs)
    QgsProject.instance().addMapLayer(vl, False)

    pr = vl.dataProvider()
    #vl.setCrs(crs)
    vl.startEditing()
    #print(vl.crs())

    fets = []
    newFields = getLayerAttributes(layer.features)
    for f in layer.features: 
        new_feat = featureToNative(f, newFields)
        if new_feat is not None and new_feat != "": fets.append(new_feat)

    # add Layer attribute fields
    pr.addAttributes(newFields.toList())
    vl.updateFields()

    pr.addFeatures(fets)
    vl.updateExtents()
    vl.commitChanges()
    layerGroup.addLayer(vl)
    #print(vl.sourceCrs().toWkt())

    rendererNew = vectorRendererToNative(layer, newFields)
    if rendererNew is None:
        symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
        rendererNew = QgsSingleSymbolRenderer(symbol)

    try: vl.setRenderer(rendererNew)
    except: pass
    
    return vl

def rasterLayerToNative(layer: RasterLayer, streamBranch: str):

    vl = None
    crs = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt) #moved up, because CRS of existing layer needs to be rewritten
    # try, in case of older version "rasterCrs" will not exist 
    try: 
        crsRasterWkt = str(layer.rasterCrs.wkt)
        crsRaster = QgsCoordinateReferenceSystem.fromWkt(layer.rasterCrs.wkt) #moved up, because CRS of existing layer needs to be rewritten
    except: 
        crsRasterWkt = str(layer.crs.wkt)
        crsRaster = crs
        logToUser(f"Raster layer {layer.name} might have been sent from the older version of plugin. Try sending it again for more accurate results.", level = 1, func = inspect.stack()[0][3])
    
    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)
    else:
        layerGroup = root.insertGroup(0,newGroupName) #root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{layer.name}'

    ######################## testing, only for receiving layers #################
    source_folder = QgsProject.instance().absolutePath()

    if(source_folder == ""):
        logToUser(f"Raster layers can only be received in an existing saved project. Layer {layer.name} will be ignored", level = 1, func = inspect.stack()[0][3])
        return None

    project = QgsProject.instance()
    projectCRS = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    #crsid = crsRaster.authid()
    #try: epsg = int(crsid.split(":")[1]) 
    #except: 
    #    epsg = int(str(projectCRS).split(":")[len(str(projectCRS).split(":"))-1].split(">")[0])

    feat = layer.features[0]
    bandNames = feat["Band names"]
    bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

    #newName = f'{streamBranch}_latest_{layer.name}'

    ###########################################################################

    ## https://opensourceoptions.com/blog/pyqgis-create-raster/
    # creating file in temporary folder: https://stackoverflow.com/questions/56038742/creating-in-memory-qgsrasterlayer-from-the-rasterization-of-a-qgsvectorlayer-wit
    
    path_fn = source_folder + "/Layers_Speckle/raster_layers/" + streamBranch+ "/" 
    if not os.path.exists(path_fn): os.makedirs(path_fn)

    fn = path_fn + layer.name + ".tif" #arcpy.env.workspace + "\\" #
    #fn = source_folder + '/' + newName.replace("/","_") + '.tif' #'_received_raster.tif'
    driver = gdal.GetDriverByName('GTiff')
    # create raster dataset
    ds = driver.Create(fn, xsize=feat["X pixels"], ysize=feat["Y pixels"], bands=feat["Band count"], eType=gdal.GDT_Float32)

    # Write data to raster band
    # No data issue: https://gis.stackexchange.com/questions/389587/qgis-set-raster-no-data-value
    for i in range(feat["Band count"]):

        rasterband = np.array(bandValues[i])
        rasterband = np.reshape(rasterband,(feat["Y pixels"], feat["X pixels"]))

        band = ds.GetRasterBand(i+1) # https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html
        
        # get noDataVal or use default
        try: 
            noDataVal = float(feat["NoDataVal"][i]) # if value available
            try: band.SetNoDataValue(noDataVal)
            except: band.SetNoDataValue(float(noDataVal))
        except: pass

        band.WriteArray(rasterband) # or "rasterband.T"
    
    # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
    pt = pointToNative(feat["displayValue"][0])
    xform = QgsCoordinateTransform(crs, crsRaster, project)
    pt.transform(xform)
    ds.SetGeoTransform([pt.x(), feat["X resolution"], 0, pt.y(), 0, feat["Y resolution"]])
    # create a spatial reference object
    srs = osr.SpatialReference()
    #  For the Universal Transverse Mercator the SetUTM(Zone, North=1 or South=2)
    srs.ImportFromWkt(crsRasterWkt)
    #srs.ImportFromEPSG(epsg) # from https://gis.stackexchange.com/questions/34082/creating-raster-layer-from-numpy-array-using-pyqgis
    #print(srs.ExportToWkt())
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
