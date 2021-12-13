import os
import math
from qgis.core import Qgis, QgsRasterLayer, QgsVectorLayer
from speckle.logging import logger
from speckle.converter.geometry import extractGeometry
from typing import Any, List

from specklepy.objects import Base


class CRS(Base):
    name: str
    wkt: str

    def __init__(self, name, wkt, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.wkt = wkt


class Layer(Base, chunkable={"features": 100}):
    def __init__(self, name, crs, features=[], **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.features = features


def getLayers(tree, parent):
    children = parent.children()
    layers = []
    for node in children:
        isLayer = tree.isLayer(node)
        if isLayer:
            layers.append(node)
            continue
        isGroup = tree.isGroup(node)
        if isGroup:
            layers.extend(getLayers(tree, node))
    return layers


def convertSelectedLayers(layers, selectedLayerNames):
    result = []
    for layer in layers:
        # if not(hasattr(layer, "fields")):
        #     continue
        if layer.name() in selectedLayerNames:
            result.append(layerToSpeckle(layer))
    return result


def layerToSpeckle(layer):
    layerName = layer.name()
    selectedLayer = layer.layer()
    crs = selectedLayer.crs()

    if isinstance(selectedLayer, QgsVectorLayer):

        fieldnames = [field.name() for field in selectedLayer.fields()]

        layerObjs = []
        # write feature attributes
        for f in selectedLayer.getFeatures():
            b = featureToSpeckle(fieldnames, f)
            layerObjs.append(b)

        # Convert CRS to speckle
        speckleCrs = CRS(name=crs.authid(), wkt=crs.toWkt())
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleCrs, layerObjs)
        layerBase.applicationId = selectedLayer.id()
        return layerBase

    if isinstance(selectedLayer, QgsRasterLayer):

        rasterLayer = RasterLayer()

        path = selectedLayer.source()
        if(os.path.exists(path)):

            f = open(path, "r")
            Lines = f.readlines()

            # calculate maximum size of one line in the raster and set chunk size accordingly
            maxSize = 0
            rasterLayer.Raster = []
            for line in Lines:
                rasterLayer.Raster.append(line)

                size = len(line.encode('utf-8'))
                if(size > maxSize):
                    maxSize = size

            f.close()

            chunkable = max(1, math.floor(1048576/size))
            rasterLayer._chunkable["Raster"] = chunkable

        return rasterLayer


def featureToSpeckle(fieldnames, f):
    b = Base()
    # Try to extract geometry
    try:
        geom = extractGeometry(f)
        if (geom != None):
            b['displayValue'] = geom
    except Exception as error:
        logger.logToUser("Error converting geometry: " + error, Qgis.Critical)

    for name in fieldnames:
        corrected = name.replace("/", "_").replace(".", "-")
        if(corrected == "id"):
            corrected == "applicationId"
        b[corrected] = str(f[name])

    return b


class RasterLayer(Base, speckle_type="Objects.Geometry." + "RasterLayer", chunkable={"Raster": 1000}, detachable={"Raster"}):
    Raster: List[str] = None

    @ classmethod
    def from_list(cls, args: List[Any]) -> "RasterLayer":
        return cls(
            Raster=args,
        )

    def to_list(self) -> List[Any]:
        return self.Raster
