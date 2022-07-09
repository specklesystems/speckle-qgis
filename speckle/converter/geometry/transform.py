
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,  QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    Qgis, QgsWkbTypes, QgsPolygon, QgsPointXY, QgsPoint, 
)

from PyQt5.QtGui import QColor


def transform(
    src: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the source CRS to the destination."""

    transformContext = QgsProject.instance().transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

    # forward transformation: src -> dest
    dest = xform.transform(src)
    return dest


def reverseTransform(
    dest: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the destination CRS to the source."""

    transformContext = QgsProject.instance().transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

    # inverse transformation: dest -> src
    src = xform.transform(dest, QgsCoordinateTransform.ReverseTransform)
    return src
