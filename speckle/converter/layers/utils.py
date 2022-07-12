from PyQt5.QtCore import QVariant
from qgis._core import Qgis, QgsVectorLayer, QgsWkbTypes, QgsField
from speckle.logging import logger
from speckle.converter.layers import Layer


def getLayerGeomType(layer: QgsVectorLayer): #https://qgis.org/pyqgis/3.0/core/Wkb/QgsWkbTypes.html 
    #print(layer.wkbType())
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


def getVariantFromValue(value):
    # TODO add Base object
    pairs = {
        str: QVariant.String,
        float: QVariant.Double,
        int: QVariant.LongLong,
        bool: QVariant.Bool
    }
    t = type(value)
    res = None
    try: res = pairs[t]
    except: pass
    return res


def get_type(type_name):
    try:
        return getattr(__builtins__, type_name)
    except AttributeError:
        try:
            obj = globals()[type_name]
        except KeyError:
            return None
        return repr(obj) if isinstance(obj, type) else None


def getLayerAttributes(layer: Layer):
    names = {}
    for feature in layer.features:
        featNames = feature.get_member_names()
        #create empty attribute fields
        for n in featNames:
            if n == "totalChildrenCount" or n == "applicationId":
                continue
            if not (n in names):
                try:
                    value = feature[n]
                    variant = getVariantFromValue(value)
                    if variant:
                        names[n] = QgsField(n, variant)
                        if n == "id": names[n] = QgsField(n, QVariant.Int)
                except Exception as error:
                    pass #print(error)
    vals = []
    sorted_names = list(names.keys())
    sorted_names.sort()
    #sort fields
    for i in sorted_names: #names.values():
        corrected = i
        #if corrected == "id": continue
        #if corrected == "applicationId": corrected = "id"
        vals.append(names[corrected])
    return vals 

def get_scale_factor(units):
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
    if units.lower() in unit_scale.keys():
        return unit_scale[units]
    logger.logToUser(f"Units {units} are not supported.", Qgis.Warning)
    return 1.0

