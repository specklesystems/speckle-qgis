"""
Contains all Layer related classes and methods.
"""
import enum
import inspect
import math
from typing import List, Tuple, Union
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh, Point, Line, Curve, Circle, Ellipse, Polycurve, Arc, Polyline 
import os
import time
from datetime import datetime

from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)
from plugin_utils.helpers import findFeatColors, findOrCreatePath, removeSpecialCharacters
#from qgis._core import Qgis, QgsVectorLayer, QgsWkbTypes
from qgis.core import (Qgis, QgsProject, QgsRasterLayer, QgsPoint, 
                       QgsVectorLayer, QgsProject, QgsWkbTypes,
                       QgsLayerTree, QgsLayerTreeGroup, QgsLayerTreeNode, QgsLayerTreeLayer,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsFields, 
                       QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
                       QgsRendererCategory,
                       QgsSymbol, QgsUnitTypes, QgsVectorFileWriter)
from specklepy.objects.GIS.geometry import GisPolygonElement
from speckle.converter.geometry.point import pointToNative, transformSpecklePt
from specklepy.objects.GIS.CRS import CRS
from specklepy.objects.GIS.layers import VectorLayer, RasterLayer, Layer
from speckle.converter.layers.feature import featureToSpeckle, rasterFeatureToSpeckle, featureToNative, cadFeatureToNative, bimFeatureToNative 
from speckle.converter.layers.utils import colorFromSpeckle, colorFromSpeckle, getElevationLayer, getLayerGeomType, getLayerAttributes, isAppliedLayerTransformByKeywords, tryCreateGroup, trySaveCRS, validateAttributeName
from speckle.converter.geometry.mesh import writeMeshToShp

from speckle.converter.layers.symbology import vectorRendererToNative, rasterRendererToNative, rendererToSpeckle

from PyQt5.QtGui import QColor
import numpy as np

from speckle.utils.panel_logging import logToUser

GEOM_LINE_TYPES = ["Objects.Geometry.Line", "Objects.Geometry.Polyline", "Objects.Geometry.Curve", "Objects.Geometry.Arc", "Objects.Geometry.Circle", "Objects.Geometry.Ellipse", "Objects.Geometry.Polycurve"]


def getAllLayers(tree: QgsLayerTree, parent: QgsLayerTreeNode = None):
    try:
        #print("Root tree: ")
        #print(tree)
        layers = []

        if parent is None:
            parent = tree 
        
        if isinstance(parent, QgsLayerTreeLayer): 
            #print("QgsLayerTreeLayer")
            #print(parent)
            return [parent.layer()] 
        
        elif isinstance(parent, QgsLayerTreeGroup): 
            #print("QgsLayerTreeGroup")
            #print(parent)
            children = parent.children()
            
            for node in children: 
                #print(node)
                if tree.isLayer(node) and isinstance(node, QgsLayerTreeLayer):
                    #print("node")
                    #print(node)
                    if isinstance(node, QgsLayerTreeLayer):
                        if isinstance(node.layer(), QgsVectorLayer) or isinstance(node.layer(), QgsRasterLayer): 
                            layers.append(node.layer())
                        continue
                elif isinstance(node, QgsLayerTreeNode):
                    try:
                        visible = node.itemVisibilityChecked()
                        #print("node layer")
                        node.setItemVisibilityChecked(True)
                        #print(node.children())
                        #print(node.checkedLayers())
                        for lyr in node.checkedLayers():
                            #print(lyr)
                            if isinstance(lyr, QgsVectorLayer) or isinstance(lyr, QgsRasterLayer): 
                                layers.append(lyr) 
                        node.setItemVisibilityChecked(visible)
                    except Exception as e: logToUser(e, level = 2, func = inspect.stack()[0][3]) 
                elif tree.isGroup(node):
                    #print("group")
                    for lyr in getAllLayers(tree, node):
                        if isinstance(lyr, QgsVectorLayer) or isinstance(lyr, QgsRasterLayer): 
                            layers.append(lyr) 
                    #layers.extend( [ lyr for lyr in getAllLayers(tree, node) if isinstance(lyr.layer(), QgsVectorLayer) or isinstance(lyr.layer(), QgsRasterLayer) ] )
        #print(layers)
        return layers
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return [parent] 

def getSavedLayers(plugin) -> List[ Union[QgsLayerTreeLayer, QgsLayerTreeNode]]:
    """Gets a list of all layers in the given QgsLayerTree"""
    
    layers = []
    try:
        project = plugin.qgis_project
        for item in plugin.dataStorage.current_layers:
            try: 
                id = item[0].id()
            except:
                logToUser(f'Saved layer not found: "{item[1]}"', level = 1, func = inspect.stack()[0][3])
                continue
            found = 0
            for l in project.mapLayers().values():
                if id == l.id():
                    layers.append(l)
                    found += 1
                    break 
            if found == 0: 
                logToUser(f'Saved layer not found: "{item[1]}"', level = 1, func = inspect.stack()[0][3])
        
        return layers
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return layers 

def getSelectedLayers(plugin) -> List[ Union[QgsLayerTreeLayer, QgsLayerTreeNode]]:
    """Gets a list of all layers in the given QgsLayerTree"""

    layers = []
    try:
        self = plugin.dockwidget
        selected_layers = plugin.iface.layerTreeView().selectedNodes()
        layers = []
        
        for item in selected_layers:
            root = self.dataStorage.project.layerTreeRoot()
            layers.extend(getAllLayers(root, item))
        return layers
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return layers 


def convertSelectedLayers(layers: List[Union[QgsVectorLayer, QgsRasterLayer]], selectedLayerIndex: List[int], selectedLayerNames: List[str], projectCRS: QgsCoordinateReferenceSystem, plugin) -> List[Union[VectorLayer, RasterLayer]]:
    """Converts the current selected layers to Speckle"""
    result = []
    try:
        project: QgsProject = plugin.qgis_project

        for i, layer in enumerate(layers):

            logToUser(f"Converting layer '{layer.name()}'...", level = 0, plugin = plugin.dockwidget)
            if plugin.dataStorage.savedTransforms is not None:
                for item in plugin.dataStorage.savedTransforms:
                    layer_name = item.split("  ->  ")[0].split(" (\'")[0]
                    transform_name = item.split("  ->  ")[1].lower()

                    # check all the conditions for transform 
                    if isinstance(layer, QgsVectorLayer) and layer.name() == layer_name and "extrude" in transform_name and "polygon" in transform_name:
                        if plugin.dataStorage.project.crs().isGeographic():
                            logToUser("Extrusion cannot be applied when the project CRS is set to Geographic type", level = 2, plugin = plugin.dockwidget)
                            return None
                        
                        attribute = None
                        if " (\'" in item:
                            attribute = item.split(" (\'")[1].split("\') ")[0]
                        if (attribute is None or str(attribute) not in layer.fields().names()) and "ignore" in transform_name:
                            logToUser("Attribute for extrusion not found", level = 2, plugin = plugin.dockwidget)
                            return None
                        
                    elif isinstance(layer, QgsRasterLayer) and layer.name() == layer_name and "elevation" in transform_name:
                        if plugin.dataStorage.project.crs().isGeographic():
                            logToUser("Raster layer transformation cannot be applied when the project CRS is set to Geographic type", level = 2, plugin = plugin.dockwidget)
                            return None
            
            result.append(layerToSpeckle(layer, projectCRS, plugin))
        
        return result
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return []


def layerToSpeckle(selectedLayer: Union[QgsVectorLayer, QgsRasterLayer], projectCRS: QgsCoordinateReferenceSystem, plugin) -> VectorLayer or RasterLayer: #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    try:
        project: QgsProject = plugin.qgis_project
        layerName = selectedLayer.name()

        crs = selectedLayer.crs()

        offset_x = plugin.dataStorage.crs_offset_x
        offset_y = plugin.dataStorage.crs_offset_y
        rotation = plugin.dataStorage.crs_rotation

        units_proj = plugin.dataStorage.currentUnits
        units_layer_native = str(QgsUnitTypes.encodeUnit(crs.mapUnits()))

        units_layer = units_layer_native
        if crs.isGeographic(): units_layer = "m" ## specklepy.logging.exceptions.SpeckleException: SpeckleException: Could not understand what unit degrees is referring to. Please enter a valid unit (eg ['mm', 'cm', 'm', 'in', 'ft', 'yd', 'mi']). 
        layerObjs = []

        # Convert CRS to speckle, use the projectCRS
        print(projectCRS.toWkt())
        speckleReprojectedCrs = CRS(authority_id=projectCRS.authid(), name=str(projectCRS.description()), wkt=projectCRS.toWkt(), units=units_proj, offset_x=offset_x, offset_y=offset_y, rotation=rotation) 
        layerCRS = CRS(authority_id=crs.authid(), name=str(crs.description()), wkt=crs.toWkt(), units=units_layer, units_native = units_layer_native, offset_x=offset_x, offset_y=offset_y, rotation=rotation) 
        
        renderer = selectedLayer.renderer()
        layerRenderer = rendererToSpeckle(renderer) 
        
        if isinstance(selectedLayer, QgsVectorLayer):

            fieldnames = [] #[str(field.name()) for field in selectedLayer.fields()]
            attributes = Base()
            for field in selectedLayer.fields():
                fieldnames.append(str(field.name()))
                corrected = validateAttributeName(str(field.name()), [])
                attribute_type = field.type()
                r'''
                all_types = [
                    (1, "bool"), 
                    (2, "int"),
                    (6, "decimal"),
                    (8, "map"),
                    (9, "int_list"),
                    (10, "string"),
                    (11, "string_list"),
                    (12, "binary"),
                    (14, "date"),
                    (15, "time"),
                    (16, "date_time") 
                ]
                for att_type in all_types:
                    if attribute_type == att_type[0]:
                        attribute_type = att_type[1]
                '''
                attributes[corrected] = attribute_type

            extrusionApplied = isAppliedLayerTransformByKeywords(selectedLayer, ["extrude", "polygon"], [], plugin.dataStorage)
            
            if extrusionApplied is True:
                if not layerName.endswith("_Mesh"): layerName += "_Mesh" 
                attributes["Speckle_ID"] = 10 # string type 

            geomType = getLayerGeomType(selectedLayer)
            features = selectedLayer.getFeatures()

            elevationLayer = getElevationLayer(plugin.dataStorage) 
            projectingApplied = isAppliedLayerTransformByKeywords(selectedLayer, ["extrude", "polygon", "project", "elevation"], [], plugin.dataStorage)
            if projectingApplied is True and elevationLayer is None:
                logToUser(f"Elevation layer is not found. Layer '{selectedLayer.name()}' will not be projected on a 3d elevation.", level = 1, plugin = plugin.dockwidget)
            
            # write features 
            for i, f in enumerate(features):
                b = featureToSpeckle(fieldnames, f, crs, projectCRS, project, selectedLayer, plugin.dataStorage)
                #if b is None: continue 

                if extrusionApplied is True and isinstance(b, GisPolygonElement):
                    b.attributes["Speckle_ID"] = str(i+1)
                    for g in b.geometry:
                        if g is not None and g!="None": 
                            # remove native polygon props, if extruded:
                                g.boundary = None
                                g.voids = None
                layerObjs.append(b)

            # Convert layer to speckle
            layerBase = VectorLayer(units = units_proj, name=layerName, crs=speckleReprojectedCrs, elements=layerObjs, attributes = attributes, geomType=geomType)
            #layerBase.type="VectorLayer"
            layerBase.renderer = layerRenderer
            layerBase.applicationId = selectedLayer.id()
            #print(layerBase.features)
            return layerBase

        if isinstance(selectedLayer, QgsRasterLayer):
            # write feature attributes
            b = rasterFeatureToSpeckle(selectedLayer, projectCRS, project, plugin)
            layerObjs.append(b)
            # Convert layer to speckle
            layerBase = RasterLayer(units = units_proj, name=layerName, crs=speckleReprojectedCrs, rasterCrs=layerCRS, elements=layerObjs)
            #layerBase.type="RasterLayer"
            layerBase.renderer = layerRenderer
            layerBase.applicationId = selectedLayer.id()
            return layerBase
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return  


def layerToNative(layer: Union[Layer, VectorLayer, RasterLayer], streamBranch: str, plugin) -> Union[QgsVectorLayer, QgsRasterLayer, None]:
    try:
        project: QgsProject = plugin.qgis_project
        #plugin.dataStorage.currentCRS = project.crs()
        plugin.dataStorage.currentUnits = layer.crs.units 
        if plugin.dataStorage.currentUnits is None or plugin.dataStorage.currentUnits == 'degrees': 
            plugin.dataStorage.currentUnits = 'm'

        
        if isinstance(layer.collectionType, str) and layer.collectionType.endswith("VectorLayer"):
            vectorLayerToNative(layer, streamBranch, plugin)
            return 
        elif isinstance(layer.collectionType, str) and layer.collectionType.endswith("RasterLayer"):
            rasterLayerToNative(layer, streamBranch, plugin)
            return 
        # if collectionType exists but not defined
        elif isinstance(layer.type, str) and layer.type.endswith("VectorLayer"): # older commits
            vectorLayerToNative(layer, streamBranch, plugin)
            return 
        elif isinstance(layer.type, str) and layer.type.endswith("RasterLayer"): # older commits
            rasterLayerToNative(layer, streamBranch, plugin)
            return 
    except:
        try: 
            if isinstance(layer.type, str) and layer.type.endswith("VectorLayer"): # older commits
                vectorLayerToNative(layer, streamBranch, plugin)
                return 
            elif isinstance(layer.type, str) and layer.type.endswith("RasterLayer"): # older commits
                rasterLayerToNative(layer, streamBranch, plugin)
                return 
            
            return 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return  


def geometryLayerToNative(layerContentList: List[Base], layerName: str, streamBranch: str, plugin):
    print("01______BIM layer to native")
    try:
        print(layerName)
        geom_meshes = []
        
        geom_points = []
        geom_polylines = []
        
        layer_points = None
        layer_polylines = None
        #geom_meshes = []
        val = None 
        
        #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
        for geom in layerContentList:

            if isinstance(geom, Point): 
                geom_points.append(geom)
                continue
            elif isinstance(geom, Line) or isinstance(geom, Polyline) or isinstance(geom, Curve) or isinstance(geom, Arc) or isinstance(geom, Circle) or isinstance(geom, Ellipse) or isinstance(geom, Polycurve):
                geom_polylines.append(geom)
                continue
            try:
                if geom.speckle_type.endswith(".ModelCurve") and geom["baseCurve"].speckle_type in GEOM_LINE_TYPES:
                    geom_polylines.append(geom["baseCurve"])
                    continue
                elif geom["baseLine"].speckle_type in GEOM_LINE_TYPES:
                    geom_polylines.append(geom["baseLine"])
                    continue
            except: pass # check for the Meshes

            # get list of display values for Meshes
            if isinstance(geom, Mesh) or isinstance(geom, List): val = geom
            else:
                try: val = geom.displayValue
                except:
                    try: val = geom["@displayValue"]
                    except:
                        try: val = geom.displayMesh
                        except: pass
            if val and isinstance(val, Mesh):
                geom_meshes.append(val)
            elif isinstance(val, List): 
                if len(val)>0 and isinstance(val[0], Mesh) : 
                    geom_meshes.extend(val)
        
        if len(geom_meshes)>0: 
            bimVectorLayerToNative(geom_meshes, layerName, "Mesh", streamBranch, plugin) 
        if len(geom_points)>0: 
            cadVectorLayerToNative(geom_points, layerName, "Points", streamBranch, plugin)
        if len(geom_polylines)>0: 
            cadVectorLayerToNative(geom_polylines, layerName, "Polylines", streamBranch, plugin)

        return True
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return  

def bimVectorLayerToNative(geomList: List[Base], layerName_old: str, geomType: str, streamBranch: str, plugin): 
    print("02_________BIM vector layer to native_____")
    try: 
        #project: QgsProject = plugin.qgis_project
        print(layerName_old)

        layerName = layerName_old[:50]
        layerName = removeSpecialCharacters(layerName) 
        print(layerName)

        #get Project CRS, use it by default for the new received layer
        vl = None
        layerName = layerName + "_" + geomType
        print(layerName)

        if "mesh" in geomType.lower(): geomType = "MultiPolygonZ"
        
        newFields = getLayerAttributes(geomList)
        print("___________Layer fields_____________")
        print(newFields.toList())
                
        plugin.dockwidget.signal_2.emit({'plugin': plugin, 'geomType': geomType, 'layerName': layerName, 'streamBranch': streamBranch, 'newFields': newFields, 'geomList': geomList})
        return 
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return  


def addBimMainThread(obj: Tuple):
    try: 
        plugin = obj['plugin'] 
        geomType = obj['geomType'] 
        layerName = obj['layerName'] 
        streamBranch = obj['streamBranch'] 
        newFields = obj['newFields'] 
        geomList = obj['geomList']
        dataStorage = plugin.dataStorage

        project: QgsProject = dataStorage.project

        newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'
        newName_shp = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{layerName}'


        ###########################################
        dummy = None 
        root = project.layerTreeRoot()
        dataStorage.all_layers = getAllLayers(root)
        if dataStorage.all_layers is not None: 
            if len(dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer("Point?crs=EPSG:4326", "", "memory") # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        
        crs = project.crs() #QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
        dataStorage.currentUnits = str(QgsUnitTypes.encodeUnit(crs.mapUnits())) 
        if dataStorage.currentUnits is None or dataStorage.currentUnits == 'degrees': 
            dataStorage.currentUnits = 'm'

        if crs.isGeographic is True: 
            logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", level = 1, func = inspect.stack()[0][3])

        p = os.path.expandvars(r'%LOCALAPPDATA%') + "\\Temp\\Speckle_QGIS_temp\\" + datetime.now().strftime("%Y-%m-%d_%H-%M")
        findOrCreatePath(p)
        path = p
        #logToUser(f"BIM layers can only be received in an existing saved project. Layer {layerName} will be ignored", level = 1, func = inspect.stack()[0][3])

        path_bim = path + "/Layers_Speckle/BIM_layers/" + streamBranch+ "/" + layerName + "/" #arcpy.env.workspace + "\\" #

        findOrCreatePath(path_bim)
        print(path_bim)

        shp = writeMeshToShp(geomList, path_bim + newName_shp, dataStorage)
        if shp is None: return 
        print("____ meshes saved___")
        print(shp)

        vl_shp = QgsVectorLayer( shp + ".shp", newName, "ogr") # do something to distinguish: stream_id_latest_name
        vl = QgsVectorLayer( geomType+ "?crs=" + crs.authid(), newName, "memory") # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        vl.startEditing()

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
                    if shape["speckle_id"] == f.id:
                        exist_feat = vl_shp.getFeature(n)
                        break
                if exist_feat is None: 
                    logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
                    continue 

                new_feat = bimFeatureToNative(exist_feat, f, vl.fields(), crs, path_bim, dataStorage)
                if new_feat is not None and new_feat != "": 
                    fetColors = findFeatColors(fetColors, f)
                    fets.append(new_feat)
                    vl.addFeature(new_feat)
                    fetIds.append(f.id)
                else:
                    logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
            except Exception as e: 
                logToUser(e, level = 2, func = inspect.stack()[0][3])
        
        vl.updateExtents()
        vl.commitChanges()
        layerGroup = tryCreateGroup(project, streamBranch)

        layerGroup.addLayer(vl)

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
                color = colorFromSpeckle(material)

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

        
        try: project.removeMapLayer(dummy)
        except: pass
        
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)


def cadVectorLayerToNative(geomList: List[Base], layerName: str, geomType: str, streamBranch: str, plugin) -> QgsVectorLayer: 
    print("___________cadVectorLayerToNative")
    try:
        project: QgsProject = plugin.qgis_project

        #get Project CRS, use it by default for the new received layer
        vl = None

        layerName = removeSpecialCharacters(layerName) 

        layerName = layerName + "_" + geomType
        print(layerName)

        newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{layerName}'

        if geomType == "Points": geomType = "PointZ"
        elif geomType == "Polylines": geomType = "LineStringZ"

        
        newFields = getLayerAttributes(geomList)
        print(newFields.toList())
        print(geomList)
        
        plugin.dockwidget.signal_3.emit({'plugin': plugin, 'geomType': geomType, 'newName': newName, 'streamBranch': streamBranch, 'newFields': newFields, 'geomList': geomList})
        return 
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return  
    
def addCadMainThread(obj: Tuple):
    try:
        plugin = obj['plugin'] 
        geomType = obj['geomType'] 
        newName = obj['newName'] 
        streamBranch = obj['streamBranch'] 
        newFields = obj['newFields'] 
        geomList = obj['geomList']

        project: QgsProject = plugin.dataStorage.project

        ###########################################
        dummy = None 
        root = project.layerTreeRoot()
        plugin.dataStorage.all_layers = getAllLayers(root)
        if plugin.dataStorage.all_layers is not None: 
            if len(plugin.dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer("Point?crs=EPSG:4326", "", "memory") # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        crs = project.crs() #QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
        plugin.dataStorage.currentUnits = str(QgsUnitTypes.encodeUnit(crs.mapUnits())) 
        if plugin.dataStorage.currentUnits is None or plugin.dataStorage.currentUnits == 'degrees': 
            plugin.dataStorage.currentUnits = 'm'
        #authid = trySaveCRS(crs, streamBranch)

        if crs.isGeographic is True: 
            logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", level = 1, func = inspect.stack()[0][3])

        
        vl = QgsVectorLayer( geomType+ "?crs=" + crs.authid() , newName, "memory") # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        vl.startEditing()
        
        
        # create list of Features (fets) and list of Layer fields (fields)
        attrs = QgsFields()
        fets = []
        fetIds = []
        fetColors = []
        for f in geomList[:]: 
            new_feat = cadFeatureToNative(f, newFields, plugin.dataStorage)
            # update attrs for the next feature (if more fields were added from previous feature)

            print("________cad feature to add") 
            if new_feat is not None and new_feat != "": 
                fets.append(new_feat)
                for a in newFields.toList(): 
                    attrs.append(a) 
                
                pr.addAttributes(newFields) # add new attributes from the current object
                fetIds.append(f.id)
                fetColors = findFeatColors(fetColors, f)
            else:
                logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])

        
        # add Layer attribute fields
        pr.addAttributes(newFields)
        vl.updateFields()

        #pr = vl.dataProvider()
        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        layerGroup = tryCreateGroup(project, streamBranch)

        layerGroup.addLayer(vl)

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

        try: 
            ################################### RENDERER 3D ###########################################
            #rend3d = QgsVectorLayer3DRenderer() # https://qgis.org/pyqgis/3.16/3d/QgsVectorLayer3DRenderer.html?highlight=layer3drenderer#module-QgsVectorLayer3DRenderer

            plugin_dir = os.path.dirname(__file__)
            renderer3d = os.path.join(plugin_dir, 'renderer3d.qml')
            print(renderer3d)

            vl.loadNamedStyle(renderer3d)
            vl.triggerRepaint()
        except: pass 

        try: project.removeMapLayer(dummy)
        except: pass
        
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
          

def vectorLayerToNative(layer: Layer or VectorLayer, streamBranch: str, plugin):
    try:
        project: QgsProject = plugin.qgis_project
        layerName = removeSpecialCharacters(layer.name) 

        #find ID of the layer with a matching name in the "latest" group 
        newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'

        # particularly if the layer comes from ArcGIS
        geomType = layer.geomType # for ArcGIS: Polygon, Point, Polyline, Multipoint, MultiPatch
        if geomType =="Point": geomType = "Point"
        elif geomType =="Polygon": geomType = "MultiPolygon"
        elif geomType =="Polyline": geomType = "MultiLineString"
        elif geomType =="Multipoint": geomType = "Point"
        elif geomType == 'MultiPatch': geomType = "Polygon"
        
        fets = []
        newFields = getLayerAttributes(layer.features)
        for f in layer.features: 
            new_feat = featureToNative(f, newFields, plugin.dataStorage)
            if new_feat is not None and new_feat != "": fets.append(new_feat)
            else:
                logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
        
        if newFields is None: 
            newFields = QgsFields()
        
        objectEmit = {'plugin': plugin, 'geomType': geomType, 'newName': newName, 'streamBranch': streamBranch, 'wkt': layer.crs.wkt, 'layer': layer, 'newFields': newFields, 'fets': fets}
        plugin.dockwidget.signal_1.emit(objectEmit)
        return 
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return  
    
def addVectorMainThread(obj: Tuple):
    try:
        plugin = obj['plugin'] 
        geomType = obj['geomType'] 
        newName = obj['newName'] 
        streamBranch = obj['streamBranch'] 
        wkt = obj['wkt']
        layer = obj['layer'] 
        newFields = obj['newFields'] 
        fets = obj['fets']

        project: QgsProject = plugin.dataStorage.project

        print(layer.name)

        ###########################################
        dummy = None 
        root = project.layerTreeRoot()
        plugin.dataStorage.all_layers = getAllLayers(root)
        if plugin.dataStorage.all_layers is not None: 
            if len(plugin.dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer("Point?crs=EPSG:4326", "", "memory") # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        crs = QgsCoordinateReferenceSystem.fromWkt(wkt) 
        srsid = trySaveCRS(crs, streamBranch)
        crs_new = QgsCoordinateReferenceSystem.fromSrsId(srsid)
        authid = crs_new.authid()
        print(authid)
        
        #################################################
        if not newName.endswith("_Mesh") and "polygon" in geomType.lower() and "Speckle_ID" in newFields.names():
            # reproject all QGIS polygon geometry to EPSG 4326 until the CRS issue is found 
            for i, f in enumerate(fets):
                #reproject
                xform = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem(4326), project)
                geometry = fets[i].geometry()
                geometry.transform(xform)
                fets[i].setGeometry(geometry)
            crs = QgsCoordinateReferenceSystem(4326)
            authid = "EPSG:4326"
        #################################################

        vl = None
        vl = QgsVectorLayer(geomType + "?crs=" + authid, newName, "memory") # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        #vl.setCrs(crs)
        vl.startEditing()
        #print(vl.crs())

        # add Layer attribute fields
        pr.addAttributes(newFields.toList())
        vl.updateFields()

        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        layerGroup = tryCreateGroup(project, streamBranch)

        #################################################
        if not newName.endswith("_Mesh") and "polygon" in geomType.lower() and "Speckle_ID" in newFields.names():

            p = os.path.expandvars(r'%LOCALAPPDATA%') + "\\Temp\\Speckle_QGIS_temp\\" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            findOrCreatePath(p)
            file_name = os.path.join(p, newName )
            print(file_name)
            print(vl)
            print(fets)
            writer = QgsVectorFileWriter.writeAsVectorFormat(vl, file_name, "utf-8", QgsCoordinateReferenceSystem(4326), "GeoJSON", overrideGeometryType = True, forceMulti = True, includeZ = True)
            del writer 

            # geojson writer fix 
            if "polygon" in geomType.lower():
                try:
                    with open(file_name + ".geojson", "r") as file:
                        lines = file.readlines()
                        polygonType = False
                        for i, line in enumerate(lines):
                            if '"type": "Polygon"' in line: 
                                polygonType = True
                                break

                        if polygonType is True:
                            new_lines = []
                            for i, line in enumerate(lines):
                                print(line)
                                if '"type": "Polygon"' in line:
                                    line = line.replace('"type": "Polygon"','"type": "MultiPolygon"')
                                if " ] ] ] " in line and '"coordinates": [ [ [ [ ' not in line: 
                                    line = line.replace(" ] ] ] ", " ] ] ] ] ")
                                if '"coordinates": [ [ [ ' in line and '"coordinates": [ [ [ [ ' not in line: 
                                    line = line.replace('"coordinates": [ [ [ ', '"coordinates": [ [ [ [ ')
                                new_lines.append(line)
                            with open(file_name + ".geojson", "w") as file:
                                file.writelines(new_lines)
                    file.close()
                except Exception as e: 
                    logToUser(e, level = 2, func = inspect.stack()[0][3])
                    return 

            vl = None 
            vl = QgsVectorLayer(file_name + ".geojson", newName, "ogr")
            #vl.setCrs(QgsCoordinateReferenceSystem(4326))
            project.addMapLayer(vl, False)
        
        #################################################

        layerGroup.addLayer(vl)

        rendererNew = vectorRendererToNative(layer, newFields)
        if rendererNew is None:
            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
            rendererNew = QgsSingleSymbolRenderer(symbol)
        
        
        #time.sleep(3)
        try: vl.setRenderer(rendererNew)
        except: pass

        try: 
            ################################### RENDERER 3D ###########################################
            #rend3d = QgsVectorLayer3DRenderer() # https://qgis.org/pyqgis/3.16/3d/QgsVectorLayer3DRenderer.html?highlight=layer3drenderer#module-QgsVectorLayer3DRenderer

            plugin_dir = os.path.dirname(__file__)
            renderer3d = os.path.join(plugin_dir, 'renderer3d.qml')
            print(renderer3d)

            vl.loadNamedStyle(renderer3d)
            vl.triggerRepaint()
        except: pass 

        try: project.removeMapLayer(dummy)
        except: pass

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
          
    
def rasterLayerToNative(layer: RasterLayer, streamBranch: str, plugin):
    try:
        #project = plugin.qgis_project
        layerName = removeSpecialCharacters(layer.name) + "_Speckle"

        newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'

        plugin.dockwidget.signal_4.emit({'plugin': plugin, 'layerName': layerName, 'newName': newName, 'streamBranch': streamBranch, 'layer': layer})
        
        return 
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
        return  

def addRasterMainThread(obj: Tuple):
    try: 
        plugin = obj['plugin'] 
        layerName = obj['layerName'] 
        newName = obj['newName'] 
        streamBranch = obj['streamBranch'] 
        layer = obj['layer'] 
        
        project: QgsProject = plugin.dataStorage.project
        dataStorage = plugin.dataStorage

        ###########################################
        dummy = None 
        root = project.layerTreeRoot()
        plugin.dataStorage.all_layers = getAllLayers(root)
        if plugin.dataStorage.all_layers is not None: 
            if len(plugin.dataStorage.all_layers) == 0:
                dummy = QgsVectorLayer("Point?crs=EPSG:4326", "", "memory") # do something to distinguish: stream_id_latest_name
                crs = QgsCoordinateReferenceSystem(4326)
                dummy.setCrs(crs)
                project.addMapLayer(dummy, True)
        #################################################

        ######################## testing, only for receiving layers #################
        source_folder = project.absolutePath()

        feat = layer.features[0]
        
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
        
        srsid = trySaveCRS(crsRaster, streamBranch)
        crs_new = QgsCoordinateReferenceSystem.fromSrsId(srsid)
        authid = crs_new.authid()

        try:
            bandNames = feat.band_names
        except: 
            bandNames = feat["Band names"]
        bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

        

        if(source_folder == ""):
            p = os.path.expandvars(r'%LOCALAPPDATA%') + "\\Temp\\Speckle_QGIS_temp\\" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            findOrCreatePath(p)
            source_folder = p
            logToUser(f"Project directory not found. Raster layers will be saved to \"{p}\".", level = 1, func = inspect.stack()[0][3], plugin = plugin.dockwidget)

        path_fn = source_folder + "/Layers_Speckle/raster_layers/" + streamBranch+ "/" 
        if not os.path.exists(path_fn): os.makedirs(path_fn)

        
        fn = path_fn + layerName + ".tif" #arcpy.env.workspace + "\\" #
        #fn = source_folder + '/' + newName.replace("/","_") + '.tif' #'_received_raster.tif'
        driver = gdal.GetDriverByName('GTiff')
        # create raster dataset
        try:
            ds = driver.Create(fn, xsize=feat.x_size, ysize=feat.y_size, bands=feat.band_count, eType=gdal.GDT_Float32)
        except: 
            ds = driver.Create(fn, xsize=feat["X pixels"], ysize=feat["Y pixels"], bands=feat["Band count"], eType=gdal.GDT_Float32)

        # Write data to raster band
        # No data issue: https://gis.stackexchange.com/questions/389587/qgis-set-raster-no-data-value
        
        try:
            b_count = int(feat.band_count) # from 2.14
        except:
            b_count = feat["Band count"]
        
        for i in range(b_count):
            rasterband = np.array(bandValues[i])
            try:
                rasterband = np.reshape(rasterband,(feat.y_size, feat.x_size))
            except:
                rasterband = np.reshape(rasterband,(feat["Y pixels"], feat["X pixels"]))

            band = ds.GetRasterBand(i+1) # https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html
            
            # get noDataVal or use default
            try: 
                try:
                    noDataVal = float(feat.noDataValue)
                except:
                    noDataVal = float(feat["NoDataVal"][i]) # if value available
                try: band.SetNoDataValue(noDataVal)
                except: band.SetNoDataValue(float(noDataVal))
            except: pass

            band.WriteArray(rasterband) # or "rasterband.T"
        
        # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
        pt = None 
        try:
            try:
                pt = QgsPoint(feat.x_origin, feat.y_origin, 0)
            except: 
                pt = QgsPoint(feat["X_min"], feat["Y_min"], 0)
        except: 
            try:
                displayVal = feat.displayValue
            except:
                displayVal = feat["displayValue"]
            if displayVal is not None:
                if isinstance(displayVal[0], Point): 
                    pt = pointToNative(displayVal[0], plugin.dataStorage)
                if isinstance(displayVal[0], Mesh): 
                    pt = QgsPoint(displayVal[0].vertices[0], displayVal[0].vertices[1])
        if pt is None:
            logToUser("Raster layer doesn't have the origin point", level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
            return 
        
        xform = QgsCoordinateTransform(crs, crsRaster, project)
        pt.transform(xform)
        try:
            ds.SetGeoTransform([pt.x(), feat.x_resolution, 0, pt.y(), 0, feat.y_resolution])
        except:
            ds.SetGeoTransform([pt.x(), feat["X resolution"], 0, pt.y(), 0, feat["Y resolution"]])
        
        # create a spatial reference object
        ds.SetProjection(crsRasterWkt)
        # close the rater datasource by setting it equal to None
        ds = None

        raster_layer = QgsRasterLayer(fn, newName, 'gdal')
        project.addMapLayer(raster_layer, False)
        
        layerGroup = tryCreateGroup(project, streamBranch)
        layerGroup.addLayer(raster_layer)

        dataProvider = raster_layer.dataProvider()
        rendererNew = rasterRendererToNative(layer, dataProvider)

        try: raster_layer.setRenderer(rendererNew)
        except: pass


        try: project.removeMapLayer(dummy)
        except: pass

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = plugin.dockwidget)
          