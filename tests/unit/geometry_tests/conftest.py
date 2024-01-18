import math
from typing import Union
import pytest

import os
import sys
import speckle

r"""
sys.path.append(
    os.path.abspath(
        os.path.dirname(speckle.__file__).replace(
            "speckle-qgis\\speckle", "speckle-qgis\\specklepy_qt_ui"
        )
    )
)
"""

# from specklepy_qt_ui.qt_ui.DataStorage import DataStorage

from specklepy.objects.encoding import CurveTypeEncoding
from specklepy.objects.geometry import Arc, Line, Mesh, Point, Plane, Polycurve, Vector


@pytest.fixture()
def data_storage():
    class DataStorage:
        crs_offset_x: Union[int, float]
        crs_offset_y: Union[int, float]
        crs_rotation: Union[int, float]

        def __init__(self):
            pass

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
    poly = Polycurve()
    segm1 = Line.from_list(
        [CurveTypeEncoding.Line.value, -10, 0, 0, -5, 0, 0, -5, 0, 0, 3]
    )
    segm2 = Line.from_list(
        [CurveTypeEncoding.Line.value, -5, 0, 0, 0, 0, 0, -5, 0, 0, 3]
    )
    # segm2 = Polyline()
    # segm3 = Arc()
    poly.segments = [segm1, segm2]  # , segm3]
    return poly


@pytest.fixture()
def mesh():
    mesh_obj = Mesh().create(
        vertices=[0, 0, 0, 100, 0, 0, 0, 100, 0], faces=[3, 0, 1, 2]
    )
    mesh.units = "m"
    return mesh_obj
