r"""
from qgis.core import (
    QgsRasterLayer,
    QgsVectorLayer,
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsLayerTreeNode,
    QgsLayerTreeLayer,
)
"""
# from speckle.converter.layers import getAllLayers


def test_get_all_layers_empty_parent():
    tree = None  # QgsLayerTree()
    parent = None
    # result = getAllLayers(tree, parent)
    # assert isinstance(result, list)
