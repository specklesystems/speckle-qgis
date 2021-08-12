from qgis.core import  QgsWkbTypes

from specklepy.objects.geometry import Point
from .logging import log
def extractGeometry(feature):
    geom = feature.geometry()
    geomSingleType = QgsWkbTypes.isSingleType(geom.wkbType())
    if geom.type() == QgsWkbTypes.PointGeometry:
        # the geometry type can be of single or multi type
        if geomSingleType:
            pt = geom.asPoint()
            return Point(x=pt.x(), y=pt.y())
        else:
            x = geom.asMultiPoint()
            info = str.join("MultiPoint: ", str(x))
            log(info)
    elif geom.type() == QgsWkbTypes.LineGeometry:
        if geomSingleType:
            x = geom.asPolyline()
            info = str.join("Line: ", str(x), " length: ", str(geom.length()))
            log(info)
        else:
            x = geom.asMultiPolyline()
            info = str.join("MultiLine: ", str(x), " length: ",str( geom.length()))
            log(info)
    elif geom.type() == QgsWkbTypes.PolygonGeometry:
        if geomSingleType:
            x = geom.asPolygon()
            info = str.join("Polygon: ", str(x),  "Area: ", str(geom.area()))
            log(info)
        else:
            x = geom.asMultiPolygon()
            info = str.join("MultiPolygon: ", str(x), " Area: ", str(geom.area()))
            log(info)
    else:
        print("Unknown or invalid geometry")
    return None