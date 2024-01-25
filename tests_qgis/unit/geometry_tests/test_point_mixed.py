from speckle.converter.geometry.point import (
    pointToSpeckle,
    pointToNative,
    pointToNativeWithoutTransforms,
)
from specklepy.objects.geometry import Point


def test_pointToSpeckle(data_storage):
    pt = Point.from_list([0, 4, 0])
    pt.units = "m"
    result = pointToSpeckle(pt, pt.units, data_storage)
    assert isinstance(result, Point)
