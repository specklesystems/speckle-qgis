from speckle.converter.features.utils import (
    addFeatVariant,
    updateFeat,
    getPolygonFeatureHeight,
)
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
def test_addFeatVariant(qgis_feature):
    key = "some key"
    variant = 10 # string
    value = "value to add"
    result = addFeatVariant(key, variant, value, qgis_feature)
    assert isinstance(result, QgsFeature)