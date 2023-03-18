
import inspect
from qgis.core import (
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,  QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsPointXY 
)

from PyQt5.QtGui import QColor

from ui.logger import logToUser


def transform(
    project: QgsProject, 
    src: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the source CRS to the destination."""
    try:
        transformContext = project.transformContext()
        xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

        # forward transformation: src -> dest
        dest = xform.transform(src)
        return dest
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
def reverseTransform(
    project: QgsProject,
    dest: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the destination CRS to the source."""
    try:
        transformContext = project.transformContext()
        xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

        # inverse transformation: dest -> src
        src = xform.transform(dest, QgsCoordinateTransform.ReverseTransform)
        return src
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
