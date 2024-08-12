import pytest


from speckle.converter.geometry.utils import (
    triangulatePolygon,
    getPolyPtsSegments,
)

try:
    from qgis.core import (
        QgsPoint,
        QgsLineString,
        QgsPolygon,
    )
except ModuleNotFoundError:
    pass


def test_triangulatePolygon(qgis_polygon, data_storage):
    result = triangulatePolygon(qgis_polygon, data_storage)
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert isinstance(result[0], dict)
    assert isinstance(result[1], list)
    assert isinstance(result[2], int)


def test_getPolyPtsSegments(qgis_polygon, data_storage):
    result = getPolyPtsSegments(qgis_polygon, data_storage, None)
    assert isinstance(result, tuple)
    assert len(result) == 4
    assert isinstance(result[0], list)
    assert isinstance(result[1], list)
    assert isinstance(result[2], list)
    assert isinstance(result[3], list)
    assert len(result[3]) == 0
