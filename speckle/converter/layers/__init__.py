"""
Contains all Layer related classes and methods.
"""

import inspect
from typing import List, Tuple, Union

try:
    from qgis.core import (
        QgsRasterLayer,
        QgsVectorLayer,
        QgsLayerTree,
        QgsLayerTreeGroup,
        QgsLayerTreeNode,
        QgsLayerTreeLayer,
    )
except ModuleNotFoundError:
    pass

from speckle.utils.panel_logging import logToUser

from plugin_utils.helpers import SYMBOL, UNSUPPORTED_PROVIDERS


def getAllLayers(
    tree: "QgsLayerTree", parent: Union["QgsLayerTreeNode", None] = None
) -> List[Union["QgsVectorLayer", "QgsRasterLayer"]]:
    try:
        layers = []
        if parent is None:
            parent = tree

        if isinstance(parent, QgsLayerTreeLayer):
            return [parent.layer()]

        elif isinstance(parent, QgsLayerTreeGroup):
            children = parent.children()

            for node in children:
                if tree.isLayer(node) and isinstance(node, QgsLayerTreeLayer):
                    if isinstance(node.layer(), QgsVectorLayer) or isinstance(
                        node.layer(), QgsRasterLayer
                    ):
                        layers.append(node.layer())
                    continue
                elif tree.isGroup(node):
                    for lyr in getAllLayers(tree, node):
                        if isinstance(lyr, QgsVectorLayer) or isinstance(
                            lyr, QgsRasterLayer
                        ):
                            layers.append(lyr)
                elif isinstance(node, QgsLayerTreeNode):
                    try:
                        visible = node.itemVisibilityChecked()
                        node.setItemVisibilityChecked(True)
                        for lyr in node.checkedLayers():
                            if isinstance(lyr, QgsVectorLayer) or isinstance(
                                lyr, QgsRasterLayer
                            ):
                                layers.append(lyr)
                        node.setItemVisibilityChecked(visible)
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])
        return layers

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return [parent]


def getAllLayersWithTree(
    tree: "QgsLayerTree",
    parent: Union["QgsLayerTreeNode", None] = None,
    existingStructure: str = "",
):
    try:
        layers = []
        tree_structure = []
        existingStructure = existingStructure.replace(SYMBOL + SYMBOL, SYMBOL)

        if parent is None:
            parent = tree

        if isinstance(parent, QgsLayerTreeLayer):
            newStructure = (existingStructure + SYMBOL).replace(SYMBOL + SYMBOL, SYMBOL)
            tree_structure.append(newStructure)
            return ([parent.layer()], tree_structure)

        elif isinstance(parent, QgsLayerTreeGroup):
            children = parent.children()

            for node in children:
                if tree.isLayer(node) and isinstance(node, QgsLayerTreeLayer):
                    if isinstance(node.layer(), QgsVectorLayer) or isinstance(
                        node.layer(), QgsRasterLayer
                    ):
                        layers.append(node.layer())
                        newStructure = (existingStructure + SYMBOL).replace(
                            SYMBOL + SYMBOL, SYMBOL
                        )
                        tree_structure.append(newStructure + parent.name())
                    continue
                elif tree.isGroup(node):
                    newStructure = (existingStructure + SYMBOL).replace(
                        SYMBOL + SYMBOL, SYMBOL
                    )
                    result = getAllLayersWithTree(
                        tree, node, newStructure + parent.name()
                    )
                    for i, lyr in enumerate(result[0]):
                        if isinstance(lyr, QgsVectorLayer) or isinstance(
                            lyr, QgsRasterLayer
                        ):
                            layers.append(lyr)
                            newStructureGroup = (
                                existingStructure + result[1][i]
                            ).replace(SYMBOL + SYMBOL, SYMBOL)
                            tree_structure.append(newStructureGroup)
                elif isinstance(node, QgsLayerTreeNode):
                    try:
                        visible = node.itemVisibilityChecked()
                        node.setItemVisibilityChecked(True)
                        for lyr in node.checkedLayers():
                            if isinstance(lyr, QgsVectorLayer) or isinstance(
                                lyr, QgsRasterLayer
                            ):
                                layers.append(lyr)
                                newStructure = (existingStructure + SYMBOL).replace(
                                    SYMBOL + SYMBOL, SYMBOL
                                )
                                tree_structure.append(newStructure + parent.name())
                        node.setItemVisibilityChecked(visible)
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

        elif isinstance(parent, QgsLayerTreeNode):
            try:
                visible = parent.itemVisibilityChecked()
                parent.setItemVisibilityChecked(True)
                for lyr in parent.checkedLayers():
                    if isinstance(lyr, QgsVectorLayer) or isinstance(
                        lyr, QgsRasterLayer
                    ):
                        layers.append(lyr)
                        newStructure = (existingStructure + SYMBOL).replace(
                            SYMBOL + SYMBOL, SYMBOL
                        )
                        tree_structure.append(newStructure + tree.name())
                parent.setItemVisibilityChecked(visible)
            except Exception as e:
                logToUser(e, level=2, func=inspect.stack()[0][3])

        return (layers, tree_structure)

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None


def findAndClearLayerGroup(root, newGroupName: str = "", plugin=None):
    try:
        layerGroup = root.findGroup(newGroupName)
        if layerGroup is None:
            return

        layersInGroup = getAllLayers(root, layerGroup)
        for lyr in layersInGroup:
            if isinstance(lyr, QgsVectorLayer):
                try:
                    lyr.getFeature(0).geometry()  # <QgsGeometry: null>
                except:
                    pass
                if "Speckle_ID" in lyr.fields().names():
                    if lyr.name().endswith(
                        ("_Mesh", "_Polyline", "_Point", "_Table")
                    ) or plugin.dataStorage.latestHostApp.lower().endswith(
                        "gis"
                    ):  # or str(lyr.wkbType()) == "WkbType.NoGeometry":
                        # print("Speckle_ID")
                        # print(lyr.name())
                        plugin.project.removeMapLayer(lyr)

            elif isinstance(lyr, QgsRasterLayer):
                if "_Speckle" in lyr.name():
                    # print(lyr.name())
                    plugin.project.removeMapLayer(lyr)

        r"""
        if layerGroup is not None or newGroupName is None:
            if newGroupName is None: layerGroup = root
            for child in layerGroup.children(): # -> List[QgsLayerTreeNode]
                if isinstance(child, QgsLayerTreeLayer): 
                    if isinstance(child.layer(), QgsVectorLayer): 
                        if "Speckle_ID" in child.layer().fields().names() and child.layer().name().lower().endswith(("_mesh", "_polylines", "_points")): 
                            plugin.project.removeMapLayer(child.layerId())
                    
                    elif isinstance(child.layer(), QgsRasterLayer): 
                        if "_Speckle" in child.layer().name(): 
                            plugin.project.removeMapLayer(child.layerId())
                else: # group
                    print(child)
                    findAndClearLayerGroup(child, None, plugin)
        """
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def order_layers(plugin, layer_selection: List[Tuple]):
    """Order selected or saved layers, extract tree structure."""

    layers = []
    tree_structure = []
    orders = []

    try:
        root = plugin.dockwidget.dataStorage.project.layerTreeRoot()
        all_layers = getAllLayersWithTree(root)

        for item in layer_selection:
            try:
                id = item[0].id()
            except AttributeError:
                id = item[0].layer().id()
            except:
                logToUser(
                    f'Saved layer not found: "{item[1]}"',
                    level=1,
                    plugin=plugin.dockwidget,
                )
                continue
            # search ID among all layers
            found = 0
            for i, lyr in enumerate(all_layers[0]):
                if id == lyr.id():
                    layers.append(lyr)
                    tree_structure.append(all_layers[1][i])
                    orders.append(i)
                    found += 1
                    break
            if found == 0:
                logToUser(
                    f'Saved layer not found: "{item[1]}"',
                    level=1,
                    plugin=plugin.dockwidget,
                )
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return None, None

    layers = [x for _, x in sorted(zip(orders, layers))]
    tree_structure = [x for _, x in sorted(zip(orders, tree_structure))]

    return layers, tree_structure


def getSavedLayers(plugin) -> List[Union["QgsLayerTreeLayer", "QgsLayerTreeNode"]]:
    """Gets a list of all layers in the given QgsLayerTree"""

    return order_layers(plugin, plugin.dataStorage.current_layers)


def getSelectedLayers(plugin) -> List[Union["QgsLayerTreeLayer", "QgsLayerTreeNode"]]:
    """Gets a list of all layers in the given QgsLayerTree"""

    return getSelectedLayersWithStructure(plugin)[0]


def getSelectedLayersWithStructure(
    plugin,
) -> List[Union["QgsLayerTreeLayer", "QgsLayerTreeNode"]]:
    """Gets a list of all layers in the given QgsLayerTree"""

    return order_layers(
        plugin, [[x, x.name()] for x in plugin.iface.layerTreeView().selectedNodes()]
    )
    try:
        selected_layers = plugin.iface.layerTreeView().selectedNodes()
        root = plugin.dockwidget.dataStorage.project.layerTreeRoot()
        return getTreeFromLayers(plugin, selected_layers, root)

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return None, None


def getTreeFromLayers(
    plugin, layers: List[Union["QgsLayerTreeLayer", "QgsLayerTreeNode"]], layerTreeRoot
) -> List[Union["QgsLayerTreeLayer", "QgsLayerTreeNode"]]:
    try:
        layers_list = []
        tree_structure_list = []
        for item in layers:
            results = getAllLayersWithTree(layerTreeRoot, item)
            for i, layer in enumerate(results[0]):
                data_provider_type = layer.providerType()
                if data_provider_type in UNSUPPORTED_PROVIDERS:
                    logToUser(
                        f"Layer '{layer.name()}' has unsupported provider type '{data_provider_type}' and cannot be sent",
                        level=2,
                        plugin=plugin.dockwidget,
                    )
                else:
                    layers_list.append(layer)
                    tree_structure_list.append(results[1][i])

        return layers_list, tree_structure_list

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return None, None
