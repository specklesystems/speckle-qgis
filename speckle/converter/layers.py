import os
import math
from qgis.core import Qgis, QgsWkbTypes, QgsPointXY, QgsGeometry, QgsFeature, QgsRasterBandStats, QgsRasterLayer, QgsVectorLayer, QgsCoordinateTransform
from speckle.logging import logger
from speckle.converter.geometry import extractGeometry, rasterToMesh
from typing import Any, List

from encodings.aliases import aliases
from osgeo import gdal ## C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo

from specklepy.objects import Base

class CRS(Base):
    name: str
    wkt: str
    units: str

    def __init__(self, name, wkt, units, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.wkt = wkt
        self.units = units

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


def convertSelectedLayers(layers, selectedLayerNames, projectCRS, project):
    result = []
    for layer in layers:
        # if not(hasattr(layer, "fields")):
        #     continue
        if layer.name() in selectedLayerNames:
            if layer.layer().crs() == projectCRS:
                reprojectedLayer = layer.layer() 
            else: 
                reprojectedLayer = reprojectLayer(layer, projectCRS, project)
            result.append(layerToSpeckle(reprojectedLayer))
    return result

def reprojectLayer(layer, targetCRS, project):

    #if isinstance(layer.layer(), QgsVectorLayer):
    ### create copy of the layer in memory
    typeGeom = QgsWkbTypes.displayString(int(layer.layer().wkbType())) #returns e.g. Point, Polygon, Line
    crsId = layer.layer().crs().authid()
    layerReprojected = QgsVectorLayer(typeGeom+"?crs="+crsId, layer.name() + "_copy", "memory")
    
    ### copy fields/attributes to the new layer
    fields = layer.layer().dataProvider().fields().toList()
    layerReprojected.dataProvider().addAttributes(fields)
    layerReprojected.updateFields()

    ### get and transform the features
    features=[f for f in layer.layer().getFeatures()]
    xform = QgsCoordinateTransform(layer.layer().crs(), targetCRS, project)
    for feature in features:
        geometry = feature.geometry()
        geometry.transform(xform)
        feature.setGeometry(geometry)

    layerReprojected.dataProvider().addFeatures(features)
    layerReprojected.setCrs(targetCRS)

    return layerReprojected
    #else:
    #    return layer.layer()

def layerToSpeckle(layer): #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    layerName = layer.name()
    selectedLayer = layer #.layer()
    crs = selectedLayer.crs()
    units = "m"
    if crs.isGeographic(): units = "degrees"
    layerObjs = []
    # Convert CRS to speckle
    speckleCrs = CRS(name=crs.authid(), wkt=crs.toWkt(), units=units)

    if isinstance(selectedLayer, QgsVectorLayer):

        fieldnames = [field.name() for field in selectedLayer.fields()]

        # write feature attributes
        for f in selectedLayer.getFeatures():
            b = featureToSpeckle(fieldnames, f)
            layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleCrs, layerObjs)
        layerBase.applicationId = selectedLayer.id()
        return layerBase

    if isinstance(selectedLayer, QgsRasterLayer):
        
        # write feature attributes
        b = rasterFeatureToSpeckle(selectedLayer)
        layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleCrs, layerObjs)
        layerBase.applicationId = selectedLayer.id()
        return layerBase

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

def rasterFeatureToSpeckle(selectedLayer):
    rasterBandCount = selectedLayer.bandCount()
    rasterBandNames = []
    rasterDimensions = [selectedLayer.width(), selectedLayer.height()]

    ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
    #rasterOriginXY = [ds.GetGeoTransform()[0],ds.GetGeoTransform()[3]]
    rasterOriginPoint = QgsPointXY(ds.GetGeoTransform()[0], ds.GetGeoTransform()[3])
    rasterResXY = [ds.GetGeoTransform()[1],ds.GetGeoTransform()[5]]
    rasterBandNoDataVal = []
    rasterBandMinVal = []
    rasterDataMaxVal = []
    rasterBandVals = []
    print(ds.GetGeoTransform()) # top left corner, (X.start, X.step,X.smth, Y.start, Y.step, Y.smth), for North hemisphere Y vals will be negative
    
    for index in range(rasterBandCount):
        rasterBandNames.append(selectedLayer.bandName(index+1))
        rb = ds.GetRasterBand(index+1)
        valMin = selectedLayer.dataProvider().bandStatistics(index+1, QgsRasterBandStats.All).minimumValue
        valMax = selectedLayer.dataProvider().bandStatistics(index+1, QgsRasterBandStats.All).maximumValue
        bandVals = rb.ReadAsArray().tolist()
        rasterBandVals.append(bandVals)
        rasterBandNoDataVal.append(rb.GetNoDataValue())
        rasterBandMinVal.append(valMin)
        rasterDataMaxVal.append(valMax)

    b = Base()
    # Try to extract geometry
    try:
        pt = QgsGeometry.fromPointXY(rasterOriginPoint)
        geom = extractGeometry(pt)
        if (geom != None):
            b['displayValue'] = geom
    except Exception as error:
        logger.logToUser("Error converting geometry: " + error, Qgis.Critical)
    
    b["X,Y resolution"] = rasterResXY
    b["X,Y dimensions"] = rasterDimensions
    b["Band count"] = str(rasterBandCount)
    b["Band names"] = str(rasterBandNames)
    #b["Band values"] = rasterBandVals
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
