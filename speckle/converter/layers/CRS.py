from specklepy.objects import Base


class CRS(Base):
    """A very basic GIS Coordinate Reference System stored in wkt format"""
    name: str
    wkt: str
    units: str

    def __init__(self, name = None, wkt = None, units = None, **kwargs) -> None:
        super().__init__(**kwargs)

        self.name = name if name != None else ""
        self.wkt = wkt if wkt != None else ""
        self.units = units if units != None else "m"