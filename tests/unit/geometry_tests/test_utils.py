import pytest

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
    getPolygonFeatureHeight,
    specklePolycurveToPoints,
    speckleArcCircleToPoints,
    speckleBoundaryToSpecklePts,
    addCorrectUnits,
    getArcRadianAngle,
    getArcAngles,
    getArcNormal,
    applyOffsetsRotation,
)

from specklepy.objects.geometry import (
    Point,
    Line,
    Mesh,
    Polyline,
    Circle,
    Arc,
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


def test_fix_orientation():
    polyBorder = [Point(-4, -4, 0), Point(0, 4, 0), Point(4, 4, 0)]
    positive = True
    coef = 1
    result = fix_orientation(polyBorder, positive, coef)
    assert result == polyBorder
