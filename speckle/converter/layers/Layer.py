from typing import Any, Dict, List, Optional
from specklepy.objects.base import Base

from speckle.converter.layers.CRS import CRS

class Layer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name:str=None,
        crs:CRS=None,
        units: str = "m",
        features: Optional[List[Base]] = None,
        layerType: str = "None",
        geomType: str = "None",
        renderer: Optional[dict[str, Any]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.units = units
        self.type = layerType
        self.features = features or []
        self.geomType = geomType
        self.renderer = renderer or {} 

class VectorLayer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name: str=None,
        crs: CRS=None,
        units: str = "m",
        features: Optional[List[Base]] = None,
        layerType: str = "None",
        geomType: str = "None",
        renderer: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.units = units
        self.type = layerType
        self.features = features or []
        self.geomType = geomType
        self.renderer = renderer or {}

class RasterLayer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name: str=None,
        crs: CRS=None,
        units: str = "m",
        rasterCrs: CRS=None,
        features: Optional[List[Base]] = None,
        layerType: str = "None",
        geomType: str = "None",
        renderer: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.units = units
        self.rasterCrs = rasterCrs
        self.type = layerType
        self.features = features or []
        self.geomType = geomType
        self.renderer = renderer or {}
