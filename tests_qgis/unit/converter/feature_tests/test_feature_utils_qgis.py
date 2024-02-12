import pytest
from speckle.converter.features.utils import (
    addFeatVariant,
    updateFeat,
    getPolygonFeatureHeight,
)

from specklepy.objects import Base
from specklepy_qt_ui.qt_ui.DataStorage import DataStorage

try:
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
except ModuleNotFoundError:
    pass


@pytest.fixture()
def data_storage():
    sample_obj = DataStorage()
    sample_obj.project = QgsProject.instance()
    return sample_obj


def test_addFeatVariant():
    key = "some key"
    variant = 10  # string
    value = "value to add"
    feature = QgsFeature()
    result = addFeatVariant(key, variant, value, feature)
    assert isinstance(result, QgsFeature)


def test_updateFeat():
    feat = QgsFeature()
    fields = QgsFields()
    fields.append(QgsField("attr1", 4))
    fields.append(QgsField("attr2", 10))
    fields.append(QgsField("attr3_attr31", 4))
    fields.append(QgsField("attr3_attr32", 4))
    feat.setFields(fields)

    base = Base()
    base.attr1 = 1
    base.attr2 = "xx"
    base.attr3 = Base()
    base.attr3.attr31 = 222
    base.attr3.attr32 = 333

    result = updateFeat(feat, fields, base)
    assert isinstance(result, QgsFeature)
    assert result["attr1"] == 1


def test_getPolygonFeatureHeight(data_storage):
    feat = QgsFeature()
    fields = QgsFields()
    fields.append(QgsField("height_m", 4))
    feat.setFields(fields)
    feat["height_m"] = 10

    geomType = "Polygon"
    layer_name = "layer1"
    layer = QgsVectorLayer(geomType + "?crs=" + "WGS84", layer_name, "memory")
    # layer.setCrs(QgsCoordinateReferenceSystem(32630))

    data_storage.project.setCrs(QgsCoordinateReferenceSystem(32630))
    data_storage.savedTransforms = []
    data_storage.savedTransforms.append(
        layer_name + " ('height_m')  ->  Extrude polygon by selected attribute"
    )
    result = getPolygonFeatureHeight(feat, layer, data_storage)
    assert result == 10


def test_getPolygonFeatureHeight_geo_crs(data_storage):
    feat = QgsFeature()
    fields = QgsFields()
    fields.append(QgsField("height_m", 4))
    feat.setFields(fields)
    feat["height_m"] = 10

    geomType = "Polygon"
    layer_name = "layer1"
    layer = QgsVectorLayer(geomType + "?crs=" + "WGS84", layer_name, "memory")

    data_storage.project.setCrs(QgsCoordinateReferenceSystem(4326))
    data_storage.savedTransforms = []
    data_storage.savedTransforms.append(
        layer_name + " ('height_m')  ->  Extrude polygon by selected attribute"
    )
    result = getPolygonFeatureHeight(feat, layer, data_storage)
    assert result is None


def test_getPolygonFeatureHeight_ignore(data_storage):
    feat = QgsFeature()
    fields = QgsFields()
    fields.append(QgsField("height_m", 4))
    feat.setFields(fields)
    feat["height_m"] = 10

    geomType = "Polygon"
    layer_name = "layer1"
    layer = QgsVectorLayer(geomType + "?crs=" + "WGS84", layer_name, "memory")
    # layer.setCrs(QgsCoordinateReferenceSystem(32630))

    data_storage.project.setCrs(QgsCoordinateReferenceSystem(32630))
    data_storage.savedTransforms = []
    data_storage.savedTransforms.append(
        layer_name
        + " ('floors')  ->  Extrude polygon by selected attribute (randomly populate)"
    )
    result = getPolygonFeatureHeight(feat, layer, data_storage)
    assert isinstance(result, int)
    assert 10 <= result <= 20
