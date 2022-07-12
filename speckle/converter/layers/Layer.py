from typing import List
from specklepy.objects.base import Base


class Layer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name=None,
        crs=None,
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 

class RasterLayer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name=None,
        crs=None,
        rasterCrs=None,
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.rasterCrs = rasterCrs
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 