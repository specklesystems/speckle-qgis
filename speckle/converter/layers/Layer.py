from typing import Any, List
from specklepy.objects.base import Base

from speckle.converter.layers.CRS import CRS

class Layer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name:str=None,
        crs:CRS=None,
        units: str = "m",
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict[str, Any] = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.units = units
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 

class VectorLayer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name:str=None,
        crs:CRS=None,
        units: str = "m",
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict[str, Any] = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.units = units
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 

class RasterLayer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name:str=None,
        crs:CRS=None,
        units: str = "m",
        rasterCrs:CRS=None,
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict[str, Any] = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.units = units
        self.rasterCrs = rasterCrs
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 