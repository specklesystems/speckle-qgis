import inspect
from qgis.core import (
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
)

from speckle.utils.panel_logging import logToUser


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
        dest = xform.transform(
            src
        )  # reverse: (dest, QgsCoordinateTransform.ReverseTransform)
        return dest  # src
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return
