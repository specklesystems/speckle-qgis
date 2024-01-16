import math
import pytest

from specklepy_qt_ui.qt_ui.DataStorage import DataStorage

from specklepy.objects.encoding import CurveTypeEncoding
from specklepy.objects.geometry import Arc, Line, Point, Plane, Polycurve, Vector


@pytest.fixture()
def data_storage():
    sample_obj = DataStorage()
    sample_obj.crs_offset_x = 0
    sample_obj.crs_offset_y = 0
    sample_obj.crs_rotation = 0
    return sample_obj


@pytest.fixture()
def arc():
    arc = Arc()
    arc.startPoint = Point.from_list([-5, 0, 0])
    arc.midPoint = Point.from_list([0, 5, 0])
    arc.endPoint = Point.from_list([5, 0, 0])
    arc.plane = Plane()
    arc.plane.origin = Point.from_list([-5, 0, 0])
    arc.units = "m"
    arc.plane.normal = Vector.from_list([0, 0, 1])
    arc.plane.origin.units = "m"
    arc.radius = 5
    arc.angleRadians = math.pi
    return arc


@pytest.fixture()
def polycurve():
    polycurve = Polycurve()
    segm1 = Line.from_list(
        [CurveTypeEncoding.Line.value, -10, 0, 0, -5, 0, 0, -5, 0, 0, 3]
    )
    segm2 = Line.from_list(
        [CurveTypeEncoding.Line.value, -5, 0, 0, 0, 0, 0, -5, 0, 0, 3]
    )
    # segm2 = Polyline()
    # segm3 = Arc()
    polycurve.segments = [segm1, segm2]  # , segm3]
    return polycurve
