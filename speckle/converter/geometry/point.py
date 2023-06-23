import inspect
import math

from qgis.core import (
    QgsPoint,
    QgsPointXY, QgsFeature, QgsVectorLayer, QgsUnitTypes
)

from specklepy.objects.geometry import Point
from speckle.converter.layers.utils import get_scale_factor, get_scale_factor_to_meter
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.utils.panel_logging import logToUser
#from PyQt5.QtGui import QColor

def pointToSpeckle(pt: QgsPoint or QgsPointXY, feature: QgsFeature, layer: QgsVectorLayer, dataStorage):
    """Converts a QgsPoint to Speckle"""
    try: 
        if isinstance(pt, QgsPointXY):
            pt = QgsPoint(pt)
        # when unset, z() returns "nan"
        x = pt.x()
        y = pt.y()
        z = 0 if math.isnan(pt.z()) else pt.z()
        specklePoint = Point()
        specklePoint.x = x
        specklePoint.y = y
        specklePoint.z = z
        specklePoint.units = "m"

        
        offset_x = dataStorage.crs_offset_x
        offset_y = dataStorage.crs_offset_y
        rotation = dataStorage.crs_rotation
        if offset_x is not None and isinstance(offset_x, float):
            x -= offset_x
        if offset_y is not None and isinstance(offset_y, float):
            y -= offset_y
        if rotation is not None and isinstance(rotation, float) and -360< rotation <360:
            a = rotation * math.pi / 180
            print(a)
            x2 = x
            y2 = y

            if a < 0: # turn counterclockwise on send
                x2 = x*math.cos(a) - y*math.sin(a)
                y2 = x*math.sin(a) + y*math.cos(a)         

            elif a > 0: # turn clockwise on send
                x2 =  x*math.cos(a) + y*math.sin(a)
                y2 = -1*x*math.sin(a) + y*math.cos(a)
            x = x2
            y = y2

        specklePoint.x = x
        specklePoint.y = y

        col = featureColorfromNativeRenderer(feature, layer)
        specklePoint['displayStyle'] = {}
        specklePoint['displayStyle']['color'] = col
        return specklePoint
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None


def pointToNative(pt: Point, dataStorage) -> QgsPoint:
    """Converts a Speckle Point to QgsPoint"""
    try:
        pt = scalePointToNative(pt, pt.units, dataStorage)
        offset_x = dataStorage.crs_offset_x
        offset_y = dataStorage.crs_offset_y
        rotation = dataStorage.crs_rotation
        if rotation is not None and isinstance(rotation, float) and -360< rotation <360:
            a = rotation * math.pi / 180
            x2 = pt.x
            y2 = pt.y

            if a > 0: # turn counterclockwise on receive
                x2 = pt.x*math.cos(a) - pt.y*math.sin(a)
                y2 = pt.x*math.sin(a) + pt.y*math.cos(a)  
            elif a < 0: # turn clockwise on receive
                x2 =  pt.x*math.cos(a) + pt.y*math.sin(a)
                y2 = -1*pt.x*math.sin(a) + pt.y*math.cos(a)       

            pt.x = x2
            pt.y = y2

        if offset_x is not None and isinstance(offset_x, float):
            pt.x += offset_x
        if offset_y is not None and isinstance(offset_y, float):
            pt.y += offset_y

        return QgsPoint(pt.x, pt.y, pt.z)
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def scalePointToNative(point: Point, units: str, dataStorage) -> Point:
    """Scale point coordinates to meters"""
    try:
        scaleFactor = get_scale_factor(units, dataStorage) # to meters
        pt = Point(units = "m")
        pt.x = point.x * scaleFactor
        pt.y = point.y * scaleFactor
        pt.z = 0 if math.isnan(point.z) else point.z * scaleFactor
        return pt
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None
