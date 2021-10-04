from qgis.core import Qgis
from specklepy.objects import Base
from ..logging import logger
from ..converter.geometry import extractGeometry

from specklepy.objects import Base 

class CRS(Base):
    name: str
    wkt: str
    def __init__(self, name, wkt, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.wkt = wkt

class Layer(Base, chunkable={"features": 100}):
    crs: CRS
    name: str
    features: Base

    def __init__(self, name, crs, features = [], **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.features = features


def convertSelectedLayers(layers, selectedLayerNames):
    result = []
    for layer in layers:
        if layer.name() in selectedLayerNames:
            result.append(layerToSpeckle(layer))
    return result

def layerToSpeckle(layer):
    layerName = layer.name()
    selectedLayer = layer.layer()
    crs = selectedLayer.crs()
    fieldnames = [field.name() for field in selectedLayer.fields()]

    layerObjs = Base()
            # write feature attributes
    for f in selectedLayer.getFeatures():
        b = featureToSpeckle(fieldnames, f)
        layerObjs["@"+str(f.id())] = b
            
            # Convert CRS to speckle
    speckleCrs = CRS(name=crs.authid(),wkt=crs.toWkt())
            # Convert layer to speckle
    layerBase = Layer(layerName,speckleCrs, layerObjs)
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

