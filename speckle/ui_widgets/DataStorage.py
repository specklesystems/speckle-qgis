
from typing import Optional
from specklepy_qt_ui.qt_ui.DataStorage import DataStorage as DataStorage_core

class DataStorage(DataStorage_core):
    geopackage_path: Optional[str] = None
    def __init__(self):
        super().__init__()
