import pytest


from speckle.converter.geometry.conversions import (
    convertToSpeckle,
    convertToNative,
    multiPointToNative,
    multiPolylineToNative,
    multiPolygonToNative,
    convertToNativeMulti,
)

from specklepy.objects import Base
from specklepy.objects.GIS.geometry import GisPolygonGeometry

from specklepy.objects.geometry import (
    Line,
    Mesh,
    Point,
    Polyline,
    Curve,
    Arc,
    Circle,
    Ellipse,
    Polycurve,
)

try:
    from qgis.core import (
        QgsPoint,
        QgsFeature,
        QgsLineString,
        QgsMultiPoint,
        QgsMultiLineString,
        QgsMultiPolygon,
        QgsPolygon,
        QgsVectorLayer,
    )
except ModuleNotFoundError:
    pass


def test_convertToSpeckle(data_storage):
    pt = QgsPoint(0, 0, 0)
    feature = QgsFeature()
    feature.setGeometry(pt)

    geomType = "Point"
    layer_name = "layer1"

    layer = QgsVectorLayer(geomType + "?crs=" + "WGS84", layer_name, "memory")

    result = convertToSpeckle(feature, layer, data_storage)
    assert isinstance(result, tuple)
    assert isinstance(result[0], Base)
    assert isinstance(result[1], int)


def test_convertToNative_pt(data_storage):
    pt = Point.from_list([0, 4, 0])
    pt.units = "m"
    result = convertToNative(pt, data_storage)
    assert isinstance(result, QgsPoint)


def test_convertToNative_polyline(polyline, data_storage):
    result = convertToNative(polyline, data_storage)
    assert isinstance(result, QgsLineString)


def test_multiPointToNative(data_storage):
    pts = [Point.from_list([0, 4, 0]) for i in range(4)]
    result = multiPointToNative(pts, data_storage)
    assert isinstance(result, QgsMultiPoint)


def test_multiPolylineToNative(polyline, data_storage):
    polylines = [polyline for i in range(4)]
    result = multiPolylineToNative(polylines, data_storage)
    assert isinstance(result, QgsMultiLineString)


def test_multiPolygonToNative(polygon, data_storage):
    polygons = [polygon for i in range(4)]
    result = multiPolygonToNative(polygons, data_storage)
    assert isinstance(result, QgsMultiPolygon)


def test_convertToNativeMulti(polygon, data_storage):
    polygons = [polygon for i in range(4)]
    result = convertToNativeMulti(polygons, data_storage)
    assert isinstance(result, QgsMultiPolygon)
