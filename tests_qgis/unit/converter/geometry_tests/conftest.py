import math
from typing import Union
import pytest
from specklepy_qt_ui.qt_ui.DataStorage import DataStorage

from specklepy.objects.encoding import CurveTypeEncoding
from specklepy.objects.geometry import (
    Arc,
    Line,
    Polyline,
    Mesh,
    Point,
    Plane,
    Polycurve,
    Vector,
)
from specklepy.objects.GIS.geometry import GisPolygonGeometry

try:
    from qgis.core import (
        QgsPoint,
        QgsLineString,
        QgsPolygon,
        QgsProject,
    )
except ModuleNotFoundError:
    pass


@pytest.fixture()
def data_storage():
    sample_obj = DataStorage()
    sample_obj.project = QgsProject.instance()
    return sample_obj


@pytest.fixture()
def qgis_polygon():
    geom = QgsPolygon()
    linestring = QgsLineString()
    linestring.addVertex(QgsPoint(4, 4, 0))
    linestring.addVertex(QgsPoint(-4, 4, 0))
    linestring.addVertex(QgsPoint(-4, -4, 0))
    linestring.addVertex(QgsPoint(4, -4, 0))

    geom.setExteriorRing(linestring)
    return geom


@pytest.fixture()
def polyline():
    polyline = Polyline()
    polyline.value = []
    polyline.closed = True
    polyline.units = "m"
    polyline.value.extend([4, 4, 0])
    polyline.value.extend([-4, 4, 0])
    polyline.value.extend([-4, -4, 0])
    polyline.value.extend([4, -4, 0])
    return polyline


@pytest.fixture()
def polygon():
    polyline = Polyline()
    polyline.value = []
    polyline.closed = True
    polyline.units = "m"
    polyline.value.extend([4, 4, 0])
    polyline.value.extend([-4, 4, 0])
    polyline.value.extend([-4, -4, 0])
    polyline.value.extend([4, -4, 0])

    polyline2 = Polyline()
    polyline2.value = []
    polyline2.closed = True
    polyline2.units = "m"
    polyline2.value.extend([4, 4, 0])
    polyline2.value.extend([-4, 4, 0])
    polyline2.value.extend([-4, -4, 0])
    polyline2.value.extend([4, -4, 0])

    geom = GisPolygonGeometry()
    geom.boundary = polyline
    geom.voids = [polyline2]
    geom.displayValue = []
    return geom


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
