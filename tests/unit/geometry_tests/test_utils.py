import math
import numpy as np
from typing import List, Tuple
import pytest
import os
import sys


def test_path():
    import speckle

    p = os.path.abspath(os.path.dirname(speckle.__file__))
    if "speckle-qgis" not in p:  # for CI
        path_add = os.path.abspath(
            os.path.dirname(speckle.__file__).replace("speckle", "specklepy_qt_ui")
        )
    else:  # for local debugging
        path_add = os.path.abspath(
            os.path.dirname(speckle.__file__).replace(
                "speckle-qgis\\speckle",
                "speckle-qgis\\specklepy_qt_ui".replace(
                    "speckle-qgis/speckle", "speckle-qgis/specklepy_qt_ui"
                ),
            )
        )
    assert "specklepy_qt_ui" in path_add
    import specklepy_qt_ui

    assert "specklepy_qt_ui" in os.path.abspath(
        os.path.dirname(specklepy_qt_ui.__file__)
    )


from speckle.converter.geometry.utils import (
    cross_product,
    dot,
    normalize,
    createPlane,
    project_to_plane_on_z,
    projectToPolygon,
    triangulatePolygon,
    to_triangles,
    trianglateQuadMesh,
    getPolyPtsSegments,
    fix_orientation,
    getHolePt,
    specklePolycurveToPoints,
    speckleArcCircleToPoints,
    speckleBoundaryToSpecklePts,
    addCorrectUnits,
    getArcRadianAngle,
    getArcAngles,
    getArcNormal,
    apply_pt_offsets_rotation_on_send,
    transform_speckle_pt_on_receive,
    apply_pt_transform_matrix,
)

from specklepy.objects import Base
from specklepy.objects.geometry import (
    Point,
    Line,
    Mesh,
    Circle,
    Arc,
    Plane,
    Polyline,
    Polycurve,
    Vector,
)


def test_cross_product_input_error():
    pt1 = [0.0, 0.0]
    pt2 = [1.0]
    with pytest.raises(ValueError) as e:
        cross_product(pt1, pt2)
    assert (
        str(e.value) == f"Not enough arguments for 3-dimentional point {pt1} or {pt2}"
    )


def test_cross_product_wrong_input_format():
    pt1 = ["0", 0.0, 0.0]
    pt2 = [0.0, 0.0, 0.0]
    try:
        cross_product(pt1, pt2)
        assert False
    except TypeError:
        assert True


def test_cross_product_zero_vectors():
    pt1 = [0.0, 0.0, 0.0]
    pt2 = [0.0, 0.0, 0.0]
    assert cross_product(pt1, pt2) == [0.0, 0.0, 0.0]


def test_dot_input_error():
    pt1 = [0.0, 0.0]
    pt2 = [1.0]
    with pytest.raises(ValueError) as e:
        dot(pt1, pt2)
    assert (
        str(e.value) == f"Not enough arguments for 3-dimentional point {pt1} or {pt2}"
    )


def test_dot_wrong_input_format():
    pt1 = ["0", 0.0, 0.0]
    pt2 = [0.0, 0.0, 0.0]
    try:
        dot(pt1, pt2)
        assert False
    except TypeError:
        assert True


def test_dot_zero_vectors():
    pt1 = [0.0, 0.0, 0.0]
    pt2 = [0.0, 0.0, 0.0]
    assert dot(pt1, pt2) == 0.0


def test_normalize_zero_vector():
    pt = [0.0, 0.0, 0.0]
    assert normalize(pt) == pt


def test_normalize_normalized_vector():
    pt = [1.0, 0.0, 0.0]
    assert normalize(pt) == pt


def test_normalize_other_vector():
    pt = [2.0, 0.0, 0.0]
    assert normalize(pt) == [1.0, 0.0, 0.0]


def test_createPlane_zero_vectors():
    pt1 = [0.0, 0.0, 0.0]
    pt2 = [0.0, 0.0, 0.0]
    pt3 = [0.0, 0.0, 0.0]
    assert createPlane(pt1, pt2, pt3) == {"origin": pt1, "normal": [0.0, 0.0, 0.0]}


def test_createPlane_input_error():
    pt1 = [0.0, 0.0]
    pt2 = [1.0]
    pt3 = [1.0]
    with pytest.raises(ValueError) as e:
        createPlane(pt1, pt2, pt3)
    assert (
        str(e.value)
        == f"Not enough arguments for 3-dimentional point {pt1}, {pt2} or {pt3}"
    )


def test_project_to_plane_basic():
    point = [0.0, 0.0, 0.0]
    plane = {"origin": point, "normal": [0.0, 0.0, 1.0]}
    assert project_to_plane_on_z(point, plane) == 0.0


def test_project_to_plane_input_error():
    point = [0.0]
    plane = {"some key": "some value"}
    with pytest.raises(ValueError) as e:
        project_to_plane_on_z(point, plane)
    assert str(e.value) == f"Invalid arguments for a point {point} or a plane {plane}"


def test_projectToPolygon_basic():
    point = [0.0, 0.0, 0.0]
    polygonPts = [[1.0, 0.0, 1.0], [0.0, 1.0, 1.0], [0.0, 2.0, 1.0]]
    assert projectToPolygon(point, polygonPts) == 1.0


def test_projectToPolygon_input_error():
    point = [0.0]
    polygonPts = [[1.0, 0.0, 1.0], [0.0, 1.0, 1.0], [0.0, 2.0, 1.0]]
    with pytest.raises(ValueError) as e:
        projectToPolygon(point, polygonPts)
    assert str(e.value) == f"Not enough arguments for a point {point}"


def test_projectToPolygon_input_error_polygon():
    point = [0.0, 0.0]
    polygonPts = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    assert projectToPolygon(point, polygonPts) == 0


def test_to_triangles_basic():
    data = {
        "vertices": [[-10, -5], [0, 5], [10, -5]],
        "holes": [[[-2, -1], [0, 1], [2, -2]]],
    }
    result = to_triangles(data)
    assert isinstance(result, tuple)
    assert isinstance(result[0]["triangles"], list)
    assert [0, 1, 2] in result[0]["triangles"]
    assert isinstance(result[0]["vertices"], list)
    assert [10.0, -5.0] in result[0]["vertices"]
    assert isinstance(result[1], int)


def test_to_triangles_invalid_shape():
    data = {
        "vertices": [[-10, -5], [0, 5], [10, -5]],
        "holes": [[[-20, -1], [0, 1], [2, -2]]],
    }
    result = to_triangles(data)
    assert isinstance(result, tuple)
    assert result[0] is None
    assert result[1] > 3


def test_trianglateQuadMesh():
    mesh = Mesh.create([-4, -4, 0, -4, 4, 0, 4, 4, 0, 4, -4, 0], [4, 0, 1, 2, 3])
    new_mesh = trianglateQuadMesh(mesh)
    assert isinstance(new_mesh, Mesh)
    assert new_mesh.faces[0] == 3
    assert len(new_mesh.vertices) == 18


def test_fix_orientation_speckle_pts():
    polyBorder = [
        Point.from_list([-4, -4, 0]),
        Point.from_list([0, 4, 0]),
        Point.from_list([4, 4, 0]),
    ]
    positive = True
    coef = 1
    result = fix_orientation(polyBorder, positive, coef)
    assert result == polyBorder


def test_getHolePt_speckle_pts():
    polyBorder = [
        Point.from_list([-4, -4, 0]),
        Point.from_list([0, 4, 0]),
        Point.from_list([4, 4, 0]),
    ]
    result = getHolePt(polyBorder)
    assert result == ([-1.999, 0.0])


def test_getArcAngles_basic(arc, data_storage):
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

    result = getArcAngles(arc, data_storage)
    assert isinstance(result, tuple)
    assert isinstance(result[0], float)


def test_getArcRadianAngle_basic(arc, data_storage):
    result = getArcRadianAngle(arc, data_storage)
    assert isinstance(result, tuple)
    assert isinstance(result[0], float)


def test_speckleArcCircleToPoints_basic(arc, data_storage):
    result = speckleArcCircleToPoints(arc, data_storage)
    assert isinstance(result, List)
    assert len(result) > 0
    assert isinstance(result[0], Point)


def test_specklePolycurveToPoints_basic(polycurve, data_storage):
    result = specklePolycurveToPoints(polycurve, data_storage)
    assert isinstance(result, List)
    assert len(result) > 0
    assert isinstance(result[0], Point)


def test_speckleBoundaryToSpecklePts_arc(arc, data_storage):
    result = speckleBoundaryToSpecklePts(arc, data_storage)
    assert isinstance(result, List)
    assert len(result) > 0
    assert isinstance(result[0], Point)


def test_speckleBoundaryToSpecklePts_polycurve(polycurve, data_storage):
    result = speckleBoundaryToSpecklePts(polycurve, data_storage)
    assert isinstance(result, List)
    assert len(result) > 0
    assert isinstance(result[0], Point)


def test_addCorrectUnits_arc(arc, data_storage):
    result = addCorrectUnits(arc, data_storage)
    assert isinstance(result, Base)
    assert result.units == data_storage.currentUnits


def test_addCorrectUnits_polycurve(polycurve, data_storage):
    result = addCorrectUnits(polycurve, data_storage)
    assert isinstance(result, Base)
    assert result.units == data_storage.currentUnits


def test_getArcNormal_basic(arc, data_storage):
    result = getArcNormal(arc, arc.midPoint, data_storage)
    assert isinstance(result, Vector)


def test_apply_pt_offsets_rotation_on_send_basic(data_storage):
    x = 0.0
    y = 10.0
    result = apply_pt_offsets_rotation_on_send(x, y, data_storage)
    assert isinstance(result, Tuple)
    assert len(result) == 2
    assert isinstance(result[0], float) and isinstance(result[1], float)
    assert result[0] == x and result[1] == y


def test_apply_pt_offsets_rotation_on_send_rotate(data_storage):
    x = 0.0
    y = 10.0
    data_storage.crs_rotation = 180
    result = apply_pt_offsets_rotation_on_send(x, y, data_storage)
    assert isinstance(result, Tuple)
    assert len(result) == 2
    assert isinstance(result[0], float) and isinstance(result[1], float)
    assert (result[0] - x) < 0.0000001 and (result[1] + y) < 0.0000001


def test_transform_speckle_pt_on_receive_rotate(data_storage):
    pt = Point.from_list([0, 4, 0])
    data_storage.crs_rotation = 180
    result = transform_speckle_pt_on_receive(pt, data_storage)
    assert isinstance(result, Point)
    assert (result.x - pt.x) < 0.0000001 and (result.y + pt.y) < 0.0000001


def test_apply_pt_transform_matrix(data_storage):
    pt = Point.from_list([0, 4, 0])
    matrixList = np.array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    matrix = np.matrix(matrixList).reshape(4, 4)
    data_storage.matrix = matrix
    result = apply_pt_transform_matrix(pt, data_storage)
    assert isinstance(result, Point)
