from typing import Optional, Union
from specklepy.objects import Base


class CRS(Base):
    """A very basic GIS Coordinate Reference System stored in wkt format"""
    name: Union[str,None]
    wkt: Union[str,None]
    x_origin: Optional[float]
    y_origin: Optional[float]
    units: Union[str,None]

    def __init__(
        self, 
        name: Union[str,None] = None, 
        wkt: Union[str,None] = None, 
        x_origin:Optional[float] = None,
        y_origin:Optional[float] = None,
        units: Union[str,None] = "m", 
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.name = name if name != None else ""
        self.wkt = wkt if wkt != None else ""
        self.x_origin = x_origin 
        self.y_origin = y_origin 
        self.units = units if units != None else "m"
