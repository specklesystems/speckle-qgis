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
                       QgsApplication,QgsSymbolLayerRegistry, QgsGradientStop)
from speckle.converter.geometry.point import pointToNative
from speckle.converter.layers.CRS import CRS
from speckle.converter.layers.Layer import Layer, RasterLayer
from speckle.converter.layers.feature import featureToSpeckle, rasterFeatureToSpeckle, featureToNative, cadFeatureToNative
from speckle.converter.layers.utils import getLayerGeomType, getVariantFromValue, getLayerAttributes
from speckle.logging import logger
from specklepy.objects import Base
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
    layerRenderer = {}

    ################## renderer values - Vector ###########################################
    renderer = selectedLayer.renderer()
    rType = renderer.type() # 'singleSymbol','categorizedSymbol','graduatedSymbol',
    layerRenderer['type'] = rType

    if rType == 'singleSymbol': 
        layerRenderer['properties'] = {'symbol':{}, 'symbType':""}

        symbol = renderer.symbol() # QgsLineSymbol
        symbType = symbol.symbolTypeToString(symbol.type()) #Line
        try: rgb = symbol.color().getRgb()
        except: rgb = symbol.color().split(',')
        symbolColor = (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
        layerRenderer['properties'].update({'symbol':{'symbColor': symbolColor}, 'symbType':symbType})

    elif rType == 'categorizedSymbol': 
        layerRenderer['properties'] = {'attribute': "", 'symbType': ""} #{'symbol':{}, 'ramp':{}, 'ranges':{}, 'gradMethod':"", 'symbType':"", 'legendClassificationAttribute': ""}
        attribute = renderer.classAttribute() # 'id'
        symbol = renderer.sourceSymbol()
        symbType = symbol.symbolTypeToString(symbol.type()) #Line

        layerRenderer['properties'].update( {'attribute': attribute, 'symbType': symbType} )
        
        categories = renderer.categories() #<qgis._core.QgsRendererCategory object at 0x00000155E8786A60>
        layerRenderer['properties']['categories'] = []
        for i in categories:
            value = i.value()
            try: rgb = i.symbol().color().getRgb()
            except: rgb = i.symbol().color().split(',')
            symbColor = (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
            symbOpacity = i.symbol().opacity() # QgsSymbol.color()
            label = i.label() 
            layerRenderer['properties']['categories'].append({'value':value,'symbColor':symbColor,'symbOpacity':symbOpacity,'label':label})
            

    elif rType == 'graduatedSymbol': 
        layerRenderer['properties'] = {'symbol':{}, 'ramp':{}, 'ranges':{}, 'gradMethod':"", 'symbType':""}

        attribute = renderer.legendClassificationAttribute() # 'id'
        symbol = renderer.sourceSymbol() # QgsLineSymbol
        symbType = symbol.symbolTypeToString(symbol.type()) #Line
        gradMethod = renderer.graduatedMethod() # 0
        layerRenderer['properties'].update( {'attribute': attribute, 'symbType': symbType, 'gradMethod': gradMethod} )

        #if isinstance(rSymbol, QgsLineSymbol):
        #    width = rSymbol.width()
        #    layerRenderer['properties']['symbol'] = {'lineWidth':width}

        rRamp = renderer.sourceColorRamp() # QgsGradientColorRamp
        if isinstance(rRamp,QgsGradientColorRamp) : 
            rgb = rRamp.color1().getRgb()
            c1 = (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
            rgb = rRamp.color2().getRgb()
            c2 = (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
            props = rRamp.properties() # {'color1': '255,255,255,255', 'color2': '255,0,0,255', 'discrete': '0', 'rampType': 'gradient'}
            stops = rRamp.stops() #[]
            rampType = rRamp.type() #'gradient'
            layerRenderer['properties']['ramp'] = props

        rRanges = renderer.ranges() # [QgsRendererRange,...]
        layerRenderer['properties']['ranges'] = []
        for i in rRanges:
            if isinstance(i, QgsRendererRange):
                lower = i.lowerValue()
                upper = i.upperValue()
                rgb = i.symbol().color().getRgb() # QgsSymbol.color() -> QColor
                symbColor = (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
                symbOpacity = i.symbol().opacity() # QgsSymbol.color()
                label = i.label() 
                # {'label': '1 - 1.4', 'lower': 1.0, 'symbColor': <PyQt5.QtGui.QColor ...BD9B9D4A0>, 'symbOpacity': 1.0, 'upper': 1.4}
                layerRenderer['properties']['ranges'].append({'lower':lower,'upper':upper,'symbColor':symbColor,'symbOpacity':symbOpacity,'label':label})
     
    #elif if rType == "singlebandgray":  
    #elif if rType == "multibandcolor":   
    #elif if rType == "paletted":   
    #elif if rType == "singlebandpseudocolor":        
    else: 
        layerRenderer = {'type': 'Other', 'properties': {}}


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


def layerToNative(layer: Union[Layer, RasterLayer], streamId: str, branchName: str) -> Union[QgsVectorLayer, QgsRasterLayer, None]:

    if layer.type is None:
        # Handle this case
        return
    elif layer.type.endswith("VectorLayer"):
        return vectorLayerToNative(layer, streamId + "_" + branchName)
    elif layer.type.endswith("RasterLayer"):
        return rasterLayerToNative(layer, streamId + "_" + branchName)
    return None

def cadLayerToNative(layerContentList:Base, layerName: str, streamId: str, branch: str) -> Union[QgsVectorLayer, QgsRasterLayer, None]:

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
    
    if len(geom_points)>0: layer_points = cadVectorLayerToNative(geom_points, layerName, "Points", streamId+"_"+branch)
    if len(geom_polylines)>0: layer_polylines = cadVectorLayerToNative(geom_polylines, layerName, "Polylines", streamId+"_"+branch)

    return [layer_points, layer_polylines]

def cadVectorLayerToNative(geomList, layerName: str, geomType: str, streamBranch: str): 
    #get Project CRS, use it by default for the new received layer
    vl = None
    layerName = layerName + "/" + geomType
    crs = QgsProject.instance().crs() #QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    if crs.isGeographic is True: 
        logger.logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", Qgis.Warning)

    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}_latest'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName) # -> QgsLayerTreeNode
    else:
        root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch}_latest{layerName}'
    childId = None
    for child in layerGroup.children(): 
        QgsProject.instance().removeMapLayer(child.layerId())
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
            try: fetColors.append(f.displayStyle.color), print(str(f.id)+ ': ' + str(f.displayStyle.color))
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
            print(r,g,b)
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
    newGroupName = f'{streamBranch}_latest'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)
    else:
        root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch}_latest/{layer.name}'
    childId = None
    for child in layerGroup.children(): 
        QgsProject.instance().removeMapLayer(child.layerId())
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
    print(attrs)
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

    ################################### RENDERER ###########################################
    # only set up renderer if the layer is just created
    renderer = layer.renderer
    if renderer and renderer['type']:
        if renderer['type']  == 'categorizedSymbol':
            attribute = renderer['properties']['attribute']
            cats = renderer['properties']['categories']

            categories = []
            noneVal = 0
            for i in range(len(cats)):
                v = cats[i]['value'] 
                if v is None: noneVal +=1
                rgb = cats[i]['symbColor']
                r = (rgb & 0xFF0000) >> 16
                g = (rgb & 0xFF00) >> 8
                b = rgb & 0xFF 
                color = QColor.fromRgb(r, g, b)
                symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(layer.geomType)))
                # create an extra category for possible future feature
                #if len(categories)==0: 
                #    symbol.setColor(QColor.fromRgb(0,0,0))
                #    categories.append(QgsRendererCategory())
                #    categories[0].setSymbol(symbol)
                #    categories[0].setLabel('Other')

                symbol.setColor(color)
                categories.append(QgsRendererCategory(cats[i]['value'], symbol, cats[i]['label'], True) )
            # create empty category for all other values (if doesn't exist yet)
            if noneVal == 0:
                symbol2 = symbol.clone()
                symbol2.setColor(QColor.fromRgb(0,0,0))
                cat = QgsRendererCategory()
                cat.setSymbol(symbol2)
                cat.setLabel('Other')
                categories.append(cat)
            
            rendererNew = QgsCategorizedSymbolRenderer(attribute, categories)

        elif renderer['type'] == 'singleSymbol':
            rgb = renderer['properties']['symbol']['symbColor']
            r = (rgb & 0xFF0000) >> 16
            g = (rgb & 0xFF00) >> 8
            b = rgb & 0xFF 
            color = QColor.fromRgb(r, g, b)
            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(layer.geomType)))
            symbol.setColor(color)
            rendererNew = QgsSingleSymbolRenderer(symbol)
        
        elif renderer['type'] == 'graduatedSymbol':
            attribute = renderer['properties']['attribute']
            gradMetod = renderer['properties']['gradMethod'] # by color or by size
            
            ramp = renderer['properties']['ramp'] # {color1, color2, discrete, rampType, stops}
            ranges = renderer['properties']['ranges'] # []
            #if ramp['rampType'] == 'gradient':
            oldStops = ramp['stops'].split(':')
            stops = []
            for i in range(len(oldStops)):
                c1,c2,c3,alpha = oldStops[i].split(';')[1].split(',')
                s = QgsGradientStop(float(oldStops[i].split(';')[0]), QColor.fromRgb(int(c1),int(c2),int(c3)) )
                stops.append(s)
            
            c11,c12,c13,alpa1 = ramp['color1'].split(',')
            color1 = QColor.fromRgb(int(c11),int(c12),int(c13))
            c21,c22,c23,alpha2 = ramp['color2'].split(',')
            color2 = QColor.fromRgb(int(c21),int(c22),int(c23))
            discrete = int(ramp['discrete'])
            newRamp = QgsGradientColorRamp(color1,color2,discrete,stops)

            newRanges = []
            for i in range(len(ranges)):
                rgb = ranges[i]['symbColor']
                r = (rgb & 0xFF0000) >> 16
                g = (rgb & 0xFF00) >> 8
                b = rgb & 0xFF 
                color = QColor.fromRgb(r, g, b)
                symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(layer.geomType)))
                symbol.setColor(color)
                newRanges.append(QgsRendererRange(ranges[i]['lower'],ranges[i]['upper'],symbol,ranges[i]['label'],True) )
            
            rendererNew = QgsGraduatedSymbolRenderer(attribute, newRanges)
            rendererNew.setSourceColorRamp(newRamp)
            rendererNew.setGraduatedMethod(gradMetod)

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
    newGroupName = f'{streamBranch}_latest'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)
    else:
        root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch}_latest/{layer.name}'
    childId = None
    for child in layerGroup.children(): 
        if child.name() == newName: 
            childId = child.layerId()
            break
    # modify existing layer (if exists) 
    if QgsProject.instance().mapLayer(childId) is not None:
        #existingRaster = QgsProject.instance().mapLayer(childId)
        QgsProject.instance().removeMapLayer(childId)

    

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
    
    return raster_layer


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
