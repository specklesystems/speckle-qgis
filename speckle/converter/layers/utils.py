import inspect
from PyQt5.QtCore import QVariant, QDate, QDateTime
from qgis._core import Qgis, QgsProject, QgsCoordinateReferenceSystem, QgsLayerTreeLayer, QgsVectorLayer, QgsRasterLayer, QgsWkbTypes, QgsField, QgsFields
from speckle.logging import logger
from speckle.converter.layers import Layer
from typing import Any, List, Tuple, Union
from specklepy.objects import Base
from specklepy.objects.geometry import Point, Line, Polyline, Circle, Arc, Polycurve, Mesh 

from PyQt5.QtGui import QColor

from osgeo import gdal, ogr, osr 
import math
import numpy as np 


from ui.logger import logToUser

ATTRS_REMOVE = ['speckleTyp','speckle_id','geometry','applicationId','bbox','displayStyle', 'id', 'renderMaterial', 'displayMesh', 'displayValue'] 

def findAndClearLayerGroup(project_gis: QgsProject, newGroupName: str = ""):
    try:
        root = project_gis.layerTreeRoot()
        
        if root.findGroup(newGroupName) is not None:
            layerGroup = root.findGroup(newGroupName)
            for child in layerGroup.children(): # -> List[QgsLayerTreeNode]
                if isinstance(child, QgsLayerTreeLayer): 
                    if isinstance(child.layer(), QgsVectorLayer): 
                        if "Speckle_ID" in child.layer().fields().names(): project_gis.removeMapLayer(child.layerId())
                    
                    elif isinstance(child.layer(), QgsRasterLayer): 
                        if "_Speckle" in child.layer().name(): project_gis.removeMapLayer(child.layerId())

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return

def getLayerGeomType(layer: QgsVectorLayer): #https://qgis.org/pyqgis/3.0/core/Wkb/QgsWkbTypes.html 
    #print(layer.wkbType())
    try:
        if layer.wkbType()==1:
            return "Point"
        elif layer.wkbType()==2001:
            return "PointM"
        elif layer.wkbType()==1001:
            return "PointZ"
        elif layer.wkbType()==3001:
            return "PointZM"

        elif layer.wkbType()==2:
            return "LineString"
        elif layer.wkbType()==2002:
            return "LineStringM"
        elif layer.wkbType()==1002:
            return "LineStringZ"
        elif layer.wkbType()==3002:
            return "LineStringZM"

        elif layer.wkbType()==3:
            return "Polygon"
        elif layer.wkbType()==2003:
            return "PolygonM"
        elif layer.wkbType()==1003:
            return "PolygonZ"
        elif layer.wkbType()==3003:
            return "PolygonZM"

        elif layer.wkbType()==4:
            return "Multipoint"
        elif layer.wkbType()==2004:
            return "MultipointM"
        elif layer.wkbType()==1004:
            return "MultipointZ"
        elif layer.wkbType()==3004:
            return "MultipointZM"

        elif layer.wkbType()==5:
            return "MultiLineString"
        elif layer.wkbType()==2005:
            return "MultiLineStringM"
        elif layer.wkbType()==1005:
            return "MultiLineStringZ"
        elif layer.wkbType()==3005:
            return "MultiLineStringZM"

        elif layer.wkbType()==6:
            return "Multipolygon"
        elif layer.wkbType()==2006:
            return "MultipolygonM"
        elif layer.wkbType()==1006:
            return "MultipolygonZ"
        elif layer.wkbType()==3006:
            return "MultipolygonZM"

        elif layer.wkbType()==7:
            return "GeometryCollection"
        elif layer.wkbType()==2007:
            return "GeometryCollectionM"
        elif layer.wkbType()==1007:
            return "GeometryCollectionZ"
        elif layer.wkbType()==3007:
            return "GeometryCollectionZM"

        elif layer.wkbType()==8:
            return "CircularString"
        elif layer.wkbType()==2008:
            return "CircularStringM"
        elif layer.wkbType()==1008:
            return "CircularStringZ"
        elif layer.wkbType()==3008:
            return "CircularStringZM"
            
        elif layer.wkbType()==9:
            return "CompoundCurve"
        elif layer.wkbType()==2009:
            return "CompoundCurveM"
        elif layer.wkbType()==1009:
            return "CompoundCurveZ"
        elif layer.wkbType()==3009:
            return "CompoundCurveZM"
            
        elif layer.wkbType()==10:
            return "CurvePolygon"
        elif layer.wkbType()==2010:
            return "CurvePolygonM"
        elif layer.wkbType()==1010:
            return "CurvePolygonZ"
        elif layer.wkbType()==3010:
            return "CurvePolygonZM"

        elif layer.wkbType()==11:
            return "MultiCurve"
        elif layer.wkbType()==2011:
            return "MultiCurveM"
        elif layer.wkbType()==1011:
            return "MultiCurveZ"
        elif layer.wkbType()==3011:
            return "MultiCurveZM"
            
        elif layer.wkbType()==12:
            return "MultiSurface"
        elif layer.wkbType()==2012:
            return "MultiSurfaceM"
        elif layer.wkbType()==1012:
            return "MultiSurfaceZ"
        elif layer.wkbType()==3012:
            return "MultiSurfaceZM"
            
        elif layer.wkbType()==17:
            return "Triangle"
        elif layer.wkbType()==2017:
            return "TriangleM"
        elif layer.wkbType()==1017:
            return "TriangleZ"
        elif layer.wkbType()==3017:
            return "TriangleZM"

        return "None"
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return


def getVariantFromValue(value: Any) -> Union[QVariant.Type, None]:
    try:
        # TODO add Base object
        pairs = {
            str: QVariant.String, # 10
            float: QVariant.Double, # 6
            int: QVariant.LongLong, # 4
            bool: QVariant.Bool,
            QDate: QVariant.Date, # 14
            QDateTime: QVariant.DateTime # 16
        }
        t = type(value)
        res = None
        try: res = pairs[t]
        except: pass

        if isinstance(value, str) and "PyQt5.QtCore.QDate(" in value: res = QVariant.Date #14
        elif isinstance(value, str) and "PyQt5.QtCore.QDateTime(" in value: res = QVariant.DateTime #16

        return res
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return

def colorFromSpeckle(rgb):
    try: 
        color = QColor.fromRgb(245,245,245) 
        if isinstance(rgb, int):
            r = (rgb & 0xFF0000) >> 16
            g = (rgb & 0xFF00) >> 8
            b = rgb & 0xFF 
            color = QColor.fromRgb(r, g, b)
        return color
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return QColor.fromRgb(245,245,245) 

def getLayerAttributes(features: List[Base]) -> QgsFields:
    try:
        #print("___________getLayerAttributes")
        fields = QgsFields()
        all_props = []
        for feature in features: 
            #get object properties to add as attributes
            dynamicProps = feature.get_dynamic_member_names()
            #attrsToRemove = ['speckleTyp','geometry','applicationId','bbox','displayStyle', 'id', 'renderMaterial', 'geometry', 'displayMesh', 'displayValue'] 
            for att in ATTRS_REMOVE:
                try: dynamicProps.remove(att)
                except: pass

            dynamicProps.sort()

            # add field names and variands 
            for name in dynamicProps:
                #if name not in all_props: all_props.append(name)

                value = feature[name]
                variant = getVariantFromValue(value)
                if not variant: variant = None #LongLong #4 

                # go thought the dictionary object
                if value and isinstance(value, list): # and isinstance(value[0], dict) :

                    for i, val_item in enumerate(value):
                        newF, newVals = traverseDict( {}, {}, name+"_"+str(i), val_item)

                        for i, (k,v) in enumerate(newF.items()):
                            if k not in all_props: all_props.append(k)
                            if k not in fields.names(): fields.append(QgsField(k, v)) # fields.update({k: v}) 
                            else: #check if the field was empty previously: 
                                index = fields.indexFromName(k)
                                oldVariant = fields.field(index).type()
                                # replace if new one is NOT Float (too large integers)
                                #if oldVariant != "FLOAT" and v == "FLOAT": 
                                #    fields.append(QgsField(k, v)) # fields.update({k: v}) 
                                # replace if new one is NOT LongLong or IS String
                                if oldVariant != QVariant.String and v == QVariant.String: 
                                    fields.append(QgsField(k, v)) # fields.update({k: v}) 

                    #all_props.remove(name) # remove generic dict name
                    #newF, newVals = traverseDict( {}, {}, name, value[0])
                    #for i, (k,v) in enumerate(newF.items()):
                    #    fields.append(QgsField(k, v)) 
                    #    if k not in all_props: all_props.append(k)
                    r'''
                    elif variant and (name not in fields.names()): 
                        fields.append(QgsField(name, variant)) 
                    
                    elif name in fields.names(): #check if the field was empty previously: 
                        nameIndex = fields.indexFromName(name)
                        oldType = fields[nameIndex].type()
                        # replace if new one is NOT LongLong or IS String
                        if oldType != QVariant.String and variant == QVariant.String: 
                            fields.append(QgsField(name,variant)) 
                    ''' 
                
                # add a field if not existing yet 
                else: # if str, Base, etc
                    newF, newVals = traverseDict( {}, {}, name, value)
                    
                    for i, (k,v) in enumerate(newF.items()):
                        if k not in all_props: all_props.append(k)
                        if k not in fields.names(): fields.append(QgsField(k, v)) # fields.update({k: v}) #if variant is known
                        else: #check if the field was empty previously: 
                            index = fields.indexFromName(k)
                            oldVariant = fields.field(index).type()
                            # replace if new one is NOT Float (too large integers)
                            #if oldVariant != "FLOAT" and v == "FLOAT": 
                            #    fields.append(QgsField(k, v)) # fields.update({k: v}) 
                            # replace if new one is NOT LongLong or IS String
                            if oldVariant != QVariant.String and v == QVariant.String: 
                                fields.append(QgsField(k, v)) # fields.update({k: v}) 

        # replace all empty ones with String
        all_props.append("Speckle_ID") 
        for name in all_props:
            if name not in fields.names(): 
                fields.append(QgsField(name, QVariant.String)) 
        
        return fields
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return

def traverseDict(newF: dict[Any, Any], newVals: dict[Any, Any], nam: str, val: Any):
    try:
        if isinstance(val, dict):
            for i, (k,v) in enumerate(val.items()):
                newF, newVals = traverseDict( newF, newVals, nam+"_"+k, v)
        elif isinstance(val, Base):
            dynamicProps = val.get_dynamic_member_names()
            for att in ATTRS_REMOVE:
                try: dynamicProps.remove(att)
                except: pass
            dynamicProps.sort()

            item_dict = {} 
            for prop in dynamicProps:
                item_dict.update({prop: val[prop]})

            for i, (k,v) in enumerate(item_dict.items()):
                newF, newVals = traverseDict( newF, newVals, nam+"_"+k, v)
        else: 
            var = getVariantFromValue(val)
            if var is None: 
                var = QVariant.String #LongLong #4 
                val = str(val)
            #else: 
            newF.update({nam: var})
            newVals.update({nam: val})  
        return newF, newVals
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return

def get_scale_factor(units: str, dataStorage ) -> float:
    scale_to_meter = get_scale_factor_to_meter(units)
    if dataStorage is not None:
        scale_back = scale_to_meter / get_scale_factor_to_meter(dataStorage.currentUnits)
        return scale_back
    else:
        return scale_to_meter

def get_scale_factor_to_meter(units: str ) -> float:
    try:
        unit_scale = {
        "meters": 1.0,
        "centimeters": 0.01,
        "millimeters": 0.001,
        "inches": 0.0254,
        "feet": 0.3048,
        "kilometers": 1000.0,
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
        "km": 1000.0,
        "in": 0.0254,
        "ft": 0.3048,
        "yd": 0.9144,
        "mi": 1609.340,
        }
        if units is not None and isinstance(units, str) and units.lower() in unit_scale.keys():
            return unit_scale[units]
        logToUser(f"Units {units} are not supported. Meters will be applied by default.", level = 1, func = inspect.stack()[0][3])
        return 1.0
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return

def validateAttributeName(name: str, fieldnames: List[str]) -> str:
    try:
        new_list = [x for x in fieldnames if x!=name]

        corrected = name.replace("/", "_").replace(".", "_")
        if corrected == "id": corrected = "applicationId"
        
        for i, x in enumerate(corrected):
            if corrected[0] != "_" and corrected not in new_list: break
            else: corrected = corrected[1:]
        
        if len(corrected)<=1 and len(name)>1: corrected = "0" + name # if the loop removed the property name completely

        return corrected
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return

def trySaveCRS(crs, streamBranch:str = ""):
    try:
        authid = crs.authid() 
        if authid =='': 
            crs_id = crs.saveAsUserCrs("SpeckleCRS_" + streamBranch)
            return crs_id
        else:
            return crs.srsid()  
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return


def reprojectPt(x, y, wkt_in, proj_in, wkt_out, proj_out):
    srs_in = osr.SpatialReference()
    srs_in.ImportFromWkt(wkt_in)
    srs_out = osr.SpatialReference()
    srs_out.ImportFromWkt(wkt_out)
    if proj_in != proj_out: 
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y) 
        point.AssignSpatialReference(srs_in) 
        point.TransformTo(srs_out) 
        newX = point.GetX()
        newY = point.GetY()
    else:
        newX = x
        newY = y
    return newX, newY 

def getArrayIndicesFromXY(settings, x, y):
    resX, resY, minX, minY, sizeX, sizeY, wkt, proj = settings 
    index1 = int( (x - minX) / resX )
    index2 = int( (y - minY) / resY )

    if not 0 <= index1 < sizeX: # try deviating +- 1
        index1 = int( (x - minX) / resX - 1 )
        if not 0 <= index1 < sizeX: 
            index1 = int( (x - minX) / resX + 1 )
    if not 0 <= index2 < sizeY:
        index2 = int( (y - minY) / resY - 1 )
        if not 0 <= index2 < sizeY:
            index2 = int( (y - minY) / resY + 1 )
    if not 0 <= index1 < sizeX or not  0 <= index2 < sizeY:
        return None, None 
    else:
        return index1, index2


def getXYofArrayPoint(settings, indexX, indexY, targetWKT, targetPROJ):
    resX, resY, minX, minY, sizeX, sizeY, wkt, proj = settings
    x = minX + resX*indexX
    y = minY + resY*indexY
    newX, newY = reprojectPt(x, y, wkt, proj, targetWKT, targetPROJ)
    return newX, newY

def isAppliedLayerTransformByKeywords(layer, keywordsYes: List[str], keywordsNo: List[str], dataStorage):
    
    correctTransform = False  
    if dataStorage.savedTransforms is not None:
        all_saved_transforms = [item.split("  ->  ")[1] for item in dataStorage.savedTransforms]
        all_saved_transform_layers = [item.split("  ->  ")[0] for item in dataStorage.savedTransforms]

        for item in dataStorage.savedTransforms:
            layer_name_recorded = item.split("  ->  ")[0]
            transform_name_recorded = item.split("  ->  ")[1]

            if layer_name_recorded == layer.name():
                if len(keywordsYes) > 0 or len(keywordsNo) > 0:
                    correctTransform = True 
                for word in keywordsYes:
                    if word in transform_name_recorded.lower(): pass 
                    else: correctTransform = False
                    break 
                for word in keywordsNo:
                    if word not in transform_name_recorded.lower(): pass 
                    else: correctTransform = False
                    break 

            #if correctTransform is True and layer_name_recorded == layer.name(): 
            #    # find a layer for meshing, if mesh transformation exists 
            #    for l in dataStorage.all_layers: 
            #        if layer_name_recorded == l.name():
            #            return l  
    return correctTransform  

def getElevationLayer(dataStorage):  
    return dataStorage.elevationLayer                
    
    if dataStorage.savedTransforms is not None:
        all_saved_transforms = [item.split("  ->  ")[1] for item in dataStorage.savedTransforms]
        all_saved_transform_layers = [item.split("  ->  ")[0] for item in dataStorage.savedTransforms]
        for item in dataStorage.savedTransforms:
            layer_name = item.split("  ->  ")[0]
            transform_name = item.split("  ->  ")[1]

            if "elevation" in transform_name.lower() and "mesh" in transform_name.lower() and "texture" not in transform_name.lower(): 
                # find a layer for meshing, if mesh transformation exists 
                for l in dataStorage.all_layers: 
                    if layer_name == l.name():
                        return l  
                        
                        # also check if the layer is selected for sending
                        for sending_l in dataStorage.sending_layers:
                            if sending_l.name() == l.name():
                                return sending_l 
    return None 

def get_raster_stats(rasterLayer):
    try:
        file_ds = gdal.Open(rasterLayer.source(), gdal.GA_ReadOnly)
        xres,yres = (float(file_ds.GetGeoTransform()[1]), float(file_ds.GetGeoTransform()[5]) )
        originX, originY = (file_ds.GetGeoTransform()[0], file_ds.GetGeoTransform()[3])
        band = file_ds.GetRasterBand(1)
        rasterWkt = file_ds.GetProjection()
        rasterProj = QgsCoordinateReferenceSystem.fromWkt(rasterWkt).toProj().replace(" +type=crs","")
        sizeX, sizeY = (band.ReadAsArray().shape[0], band.ReadAsArray().shape[1])

        return xres, yres, originX, originY, sizeX, sizeY, rasterWkt, rasterProj
    except:
        return None, None,  None, None, None, None, None, None



def getRasterArrays(elevationLayer): 
    const = float(-1* math.pow(10,30))

    try:
        elevationSource = gdal.Open(elevationLayer.source(), gdal.GA_ReadOnly)
        settings_elevation_layer = get_raster_stats(elevationLayer)
        xres, yres, originX, originY, sizeX, sizeY, rasterWkt, rasterProj = settings_elevation_layer
        
        all_arrays = []
        all_mins = []
        all_maxs = []
        all_na = []

        for b in range(elevationLayer.bandCount()):
            band = elevationSource.GetRasterBand(b+1)
            val_NA = band.GetNoDataValue()
            
            array_band = band.ReadAsArray()
            fakeArray = np.where( (array_band < const) | (array_band > -1*const) | (array_band == val_NA) | (np.isinf(array_band) ), np.nan, array_band)
            
            val_Min = np.nanmin(fakeArray)
            val_Max = np.nanmax(fakeArray)

            all_arrays.append(fakeArray) 
            all_mins.append(val_Min)
            all_maxs.append(val_Max)  
            all_na.append(val_NA)

        return (all_arrays, all_mins, all_maxs, all_na)
    except: 
        return (None, None, None, None)

def moveVertically(poly, height):

    if isinstance(poly, Polycurve):
        for segm in poly.segments:
            segm = moveVerticallySegment(segm, height)
    else:
        poly = moveVerticallySegment(poly, height)

    return poly

def moveVerticallySegment(poly, height):
    if isinstance(poly, Arc) or isinstance(poly, Circle): # or isinstance(segm, Curve):
        if poly.plane is not None:
            poly.plane.normal.z += height
            poly.plane.origin.z += height
        poly.startPoint.z += height
        try: 
            poly.endPoint.z += height
        except: pass 
    elif isinstance(poly, Line): 
        poly.start.z += height
        poly.end.z += height
    elif isinstance(poly, Polyline): 
        for i in range(len(poly.value)): 
            if (i+1) %3 == 0:
                poly.value[i] += float(height) 
    
    return poly 

