from PyQt5.QtCore import QVariant, QDate, QDateTime
from qgis._core import Qgis, QgsVectorLayer, QgsWkbTypes, QgsField, QgsFields
from speckle.logging import logger
from speckle.converter.layers import Layer
from typing import Any, List, Tuple, Union
from specklepy.objects import Base

ATTRS_REMOVE = ['speckleTyp','geometry','applicationId','bbox','displayStyle', 'id', 'renderMaterial', 'displayMesh', 'displayValue'] 

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


def getVariantFromValue(value: Any) -> Union[QVariant.Type, None]:
    # TODO add Base object
    pairs = {
        str: QVariant.String, # 10
        float: QVariant.Double,
        int: QVariant.LongLong,
        bool: QVariant.Bool,
        QDate: QVariant.Date,
        QDateTime: QVariant.DateTime
    }
    t = type(value)
    res = None
    try: res = pairs[t]
    except: pass

    if isinstance(value, str) and "PyQt5.QtCore.QDate(" in value: res = QVariant.Date #14
    elif isinstance(value, str) and "PyQt5.QtCore.QDateTime(" in value: res = QVariant.DateTime #16

    return res

def getLayerAttributes(features: List[Base]) -> QgsFields:
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
                            oldVariant = fields[k]
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
                        oldVariant = fields[k]
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

def traverseDict(newF: dict[Any, Any], newVals: dict[Any, Any], nam: str, val: Any):

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

def get_scale_factor(units: str) -> float:
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
    if units is not None and units.lower() in unit_scale.keys():
        return unit_scale[units]
    logger.logToUser(f"Units {units} are not supported. Meters will be applied by default.", Qgis.Warning)
    return 1.0

