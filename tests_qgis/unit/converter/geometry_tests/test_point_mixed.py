from speckle.converter.geometry.point import (
    pointToSpeckle,
    pointToNative,
    pointToNativeWithoutTransforms,
)
from specklepy.objects.geometry import Point

try:
    from qgis.core import (
        QgsPoint, QgsFeature, QgsVectorLayer
    )
except ModuleNotFoundError:
    pass

def test_pointToSpeckle(data_storage):
    pt = QgsPoint(0,0,0)
    feature = QgsFeature()
    feature.setGeometry(pt)

    geomType = "Point"
    layer_name = "layer1"

    layer = QgsVectorLayer(
            geomType + "?crs=" + "WGS84", layer_name, "memory"
        )
    xform = None
    result = pointToSpeckle(pt, feature, layer, data_storage, xform)
    assert isinstance(result, Point)


def test_pointToNative(data_storage):
    pt = Point.from_list([0, 4, 0])
    result = pointToNative(pt, data_storage)
    assert isinstance(result, QgsPoint)


def test_pointToNativeWithoutTransforms(data_storage):
    pt = Point.from_list([0, 4, 0])
    result = pointToNativeWithoutTransforms(pt, data_storage)
    assert isinstance(result, QgsPoint)

