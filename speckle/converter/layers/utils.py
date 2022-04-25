from PyQt5.QtCore import QVariant
from qgis._core import QgsVectorLayer, QgsWkbTypes, QgsField
from speckle.logging import logger

from speckle.converter.layers import Layer


def getLayerGeomType(layer: QgsVectorLayer): #https://qgis.org/pyqgis/3.0/core/Wkb/QgsWkbTypes.html 
    #print(layer.wkbType())
    if layer.wkbType()==QgsWkbTypes.Point or layer.wkbType()==1:
        return "Point"
    if layer.wkbType()==QgsWkbTypes.MultiPoint or layer.wkbType()==4:
        return "Multipoint"
    if layer.wkbType()== QgsWkbTypes.MultiLineString or layer.wkbType()==5:
        return "MultiLineString"
    if layer.wkbType()==11:
        return "MultiCurve"
    if layer.wkbType()==QgsWkbTypes.LineString or layer.wkbType()==2:
        return "LineString"
    if layer.wkbType()==QgsWkbTypes.Polygon or layer.wkbType()==3 or layer.wkbType()==10:
        return "Polygon"
    if layer.wkbType()==QgsWkbTypes.MultiPolygon or layer.wkbType()==6:
        return "Multipolygon"
    if layer.wkbType()==1006:
        return "MultipolygonZ"

    return "None"


def getVariantFromValue(value):
    pairs = {
        str: QVariant.String,
        float: QVariant.Double,
        int: QVariant.Int,
        bool: QVariant.Bool
    }
    t = type(value)
    return pairs[t]


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
        #print(featNames)
        for n in featNames:
            if n == "totalChildrenCount":
                continue
            if not (n in names):
                try:
                    value = feature[n]
                    variant = getVariantFromValue(value)
                    if variant:
                        names[n] = QgsField(n, variant)
                except Exception as error:
                    pass #print(error)
    vals = []
    for i in names.values():
        vals.append(i)
    #print(vals)
    return vals #[i for i in names.values()]