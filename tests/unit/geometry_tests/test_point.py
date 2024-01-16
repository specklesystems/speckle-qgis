from speckle.converter.geometry.point import (
    scalePointToNative,
)
from specklepy.objects.geometry import Point


def test_scalePointToNative(data_storage):
    pt = Point.from_list([0, 4, 0])
    pt.units = "m"
    result = scalePointToNative(pt, pt.units, data_storage)
    assert isinstance(result, Point)
