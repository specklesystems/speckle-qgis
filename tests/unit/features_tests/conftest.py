import math
from typing import Union
import pytest
from specklepy_qt_ui.qt_ui.DataStorage import DataStorage

from specklepy.objects.encoding import CurveTypeEncoding
from specklepy.objects.geometry import Arc, Line, Mesh, Point, Plane, Polycurve, Vector
from qgis._core import (
    QgsCoordinateTransform,
    Qgis,
    QgsPointXY,
    QgsGeometry,
    QgsRasterBandStats,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsUnitTypes,
)

@pytest.fixture()
def qgis_feature():
    sample_obj = QgsFeature()
    return sample_obj

