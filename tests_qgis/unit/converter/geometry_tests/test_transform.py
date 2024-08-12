import pytest

from speckle.converter.geometry.transform import transform

try:
    from qgis.core import (
        QgsProject,
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsPointXY,
        QgsProject,
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsPointXY,
    )
except ModuleNotFoundError:
    pass


def test_transform(data_storage):
    project = data_storage.project
    pt = QgsPointXY(0, 0)
    crsSrc = QgsCoordinateReferenceSystem(4326)
    crsDest = QgsCoordinateReferenceSystem(4326)
    result = transform(project, pt, crsSrc, crsDest)
    assert isinstance(result, QgsPointXY)
    assert result == pt
