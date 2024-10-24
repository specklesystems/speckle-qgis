from copy import copy
import inspect
from math import atan
import math
import numpy as np
from specklepy.objects.geometry import (
    Point,
    Line,
    Polyline,
    Curve,
    Arc,
    Circle,
    Ellipse,
    Polycurve,
    Plane,
)
from speckle.converter.geometry.point import pointToNative, pointToSpeckle

try:
    from qgis.core import (
        QgsGeometry,
        QgsLineString,
        QgsCompoundCurve,
        QgsCircularString,
        QgsCircle,
        QgsFeature,
        QgsVectorLayer,
        QgsVertexIterator,
        QgsEllipse,
        QgsWkbTypes,
    )
except ModuleNotFoundError:
    pass

from speckle.converter.geometry.utils import (
    addCorrectUnits,
    getArcNormal,
    getArcRadianAngle,
    speckleArcCircleToPoints,
)

from plugin_utils.helpers import get_scale_factor
from typing import List, Tuple, Union
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.utils.panel_logging import logToUser


def polylineFromVerticesToSpeckle(
    vertices: Union[List[Point], "QgsVertexIterator"],
    closed: bool,
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    dataStorage,
):
    """Returns a Speckle Polyline given a list of QgsPoint instances and a boolean indicating if it's closed or not."""
    try:
        specklePts: List[Point] = []
        if isinstance(vertices, list):
            if len(vertices) > 0 and isinstance(vertices[0], Point):
                specklePts = vertices
            else:
                for pt in vertices:
                    speckle_pt = pointToSpeckle(pt, feature, layer, dataStorage)
                    if speckle_pt is not None:
                        specklePts.append(speckle_pt)
        elif isinstance(vertices, QgsVertexIterator):
            for pt in vertices:
                speckle_pt = pointToSpeckle(pt, feature, layer, dataStorage)
                if speckle_pt is not None:
                    specklePts.append(speckle_pt)
        else:
            return None

        if len(specklePts) == 0 or specklePts[0] is None:
            logToUser("Polyline conversion failed", level=2)
            return

        # TODO: Replace with `from_points` function when fix is pushed.
        polyline = Polyline()
        polyline.value = []
        polyline.closed = closed
        polyline.units = specklePts[0].units
        for i, point in enumerate(specklePts):
            if (
                closed
                and i == len(specklePts) - 1
                and specklePts[0].x == specklePts[len(specklePts) - 1].x
                and specklePts[0].y == specklePts[len(specklePts) - 1].y
                and specklePts[0].z == specklePts[len(specklePts) - 1].z
            ):
                continue
            polyline.value.extend([point.x, point.y, point.z])

        col = featureColorfromNativeRenderer(feature, layer)
        polyline["displayStyle"] = {}
        polyline["displayStyle"]["color"] = col
        return polyline
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def unknownLineToSpeckle(
    poly_original: Union["QgsLineString", "QgsCompoundCurve"],
    closed: bool,
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    dataStorage,
    xform=None,
) -> Union[Polyline, Arc, Line, Polycurve, None]:
    try:
        if isinstance(poly_original, QgsGeometry):
            poly_original = poly_original.constGet()
        poly = poly_original.clone()

        if poly.wkbType() == 10:  # CurvePolygon
            # actualGeom = poly.constGet()
            actualGeom = actualGeom.segmentize()
            if xform is not None:
                actualGeom.transform(xform)
            return polylineToSpeckle(actualGeom, feature, layer, dataStorage)

        elif isinstance(poly, QgsCompoundCurve):
            return compoudCurveToSpeckle(poly, feature, layer, dataStorage, xform)
        elif isinstance(poly, QgsCircularString):
            return arcToSpeckle(poly, feature, layer, dataStorage, xform)
        else:
            if xform is not None:
                poly.transform(xform)
            return polylineFromVerticesToSpeckle(
                poly.vertices(), closed, feature, layer, dataStorage
            )  # initial method

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def compoudCurveToSpeckle(
    poly_original: "QgsCompoundCurve",
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    dataStorage,
    xform=None,
):
    try:
        if isinstance(poly_original, QgsGeometry):
            poly_original = poly_original.constGet()
        poly = poly_original.clone()

        new_poly = poly.curveToLine()
        if xform is not None:
            new_poly.transform(xform)
        return polylineToSpeckle(new_poly, feature, layer, dataStorage)

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def anyLineToSpeckle(geom_original, feature, layer, dataStorage, xform=None):
    if isinstance(geom_original, QgsGeometry):
        geom_original = geom_original.constGet()
    geom = geom_original.clone()

    type = geom.wkbType()
    if (
        type == QgsWkbTypes.CircularString
        or type == QgsWkbTypes.CircularStringZ
        or type == QgsWkbTypes.CircularStringM
        or type == QgsWkbTypes.CircularStringZM
    ):
        all_pts = [pt for pt in geom.vertices()]
        if len(all_pts) == 3:
            result = arcToSpeckle(geom, feature, layer, dataStorage, xform)
        else:
            result = compoudCurveToSpeckle(geom, feature, layer, dataStorage, xform)

    elif (
        type == QgsWkbTypes.CompoundCurve
        or type == QgsWkbTypes.CompoundCurveZ
        or type == QgsWkbTypes.CompoundCurveM
        or type == QgsWkbTypes.CompoundCurveZM
    ):  # 9, 1009, 2009, 3009
        if "CircularString" in str(geom):
            all_pts = [pt for pt in geom.vertices()]
            if len(all_pts) == 3:
                result = arcToSpeckle(geom, feature, layer, dataStorage, xform)
            else:
                result = compoudCurveToSpeckle(geom, feature, layer, dataStorage, xform)
        else:
            result = compoudCurveToSpeckle(geom, feature, layer, dataStorage, xform)
            # return None
    else:
        if xform is not None:
            geom.transform(xform)
        result = polylineToSpeckle(geom, feature, layer, dataStorage)

    result = addCorrectUnits(result, dataStorage)
    return result


def polylineToSpeckle(
    poly: Union["QgsLineString", "QgsCircularString"],
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    dataStorage,
):
    """Converts a QgsLineString to Speckle"""
    try:
        try:
            closed = poly.isClosed()
        except:
            closed = False

        polyline = polylineFromVerticesToSpeckle(
            poly.vertices(), closed, feature, layer, dataStorage
        )

        return polyline
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def arcToSpeckle(
    poly: Union["QgsCircularString", "QgsGeometry"],
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    dataStorage,
    xform=None,
):
    """Converts a QgsCircularString to Speckle"""
    try:
        poly: QgsCircularString = poly.constGet()
    except:
        pass
    try:
        # convert to polyline due to geometry distorsions
        # in case of crs transformations on send
        linestring = poly.curveToLine()
        if xform is not None:
            linestring.transform(xform)
        arc = polylineToSpeckle(linestring, feature, layer, dataStorage)
        col = featureColorfromNativeRenderer(feature, layer)
        arc["displayStyle"] = {}
        arc["displayStyle"]["color"] = col
        return arc
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def getArcCenter(
    p1: Point, p2: Point, p3: Point, dataStorage
) -> Tuple[List[float], float]:
    try:
        p1 = np.array(p1.to_list())
        p2 = np.array(p2.to_list())
        p3 = np.array(p3.to_list())
        a = np.linalg.norm(p3 - p2)
        b = np.linalg.norm(p3 - p1)
        c = np.linalg.norm(p2 - p1)
        s = (a + b + c) / 2
        radius = a * b * c / 4 / np.sqrt(s * (s - a) * (s - b) * (s - c))
        b1 = a * a * (b * b + c * c - a * a)
        b2 = b * b * (a * a + c * c - b * b)
        b3 = c * c * (a * a + b * b - c * c)
        center = np.column_stack((p1, p2, p3)).dot(np.hstack((b1, b2, b3)))
        center /= b1 + b2 + b3
        center = center.tolist()
        return center, radius
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None


def lineToNative(line: Line, dataStorage) -> "QgsLineString":
    """Converts a Speckle Line to QgsLineString"""
    try:
        line = QgsLineString(
            pointToNative(line.start, dataStorage), pointToNative(line.end, dataStorage)
        )
        return line
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def polylineToNative(poly: Polyline, dataStorage) -> "QgsLineString":
    """Converts a Speckle Polyline to QgsLineString"""
    try:
        # this function can be called from Multipolyline, hence extra check if the type of segment in not Polyline
        if isinstance(poly, Polycurve):
            return polycurveToNative(poly, dataStorage)
        elif isinstance(poly, Arc):
            return arcToNative(poly, dataStorage)
        elif isinstance(poly, Circle):
            return circleToNative(poly, dataStorage)
        elif isinstance(poly, Ellipse):
            return ellipseToNative(poly, dataStorage)

        if isinstance(poly, Curve):
            poly = poly.displayValue

        if isinstance(poly, Polyline) and poly.closed is False:
            polyline = QgsLineString(
                [pointToNative(pt, dataStorage) for pt in poly.as_points()]
            )
        else:  # Line or open Polyline
            ptList = poly.as_points()
            ptList.append(ptList[0])
            polyline = QgsLineString([pointToNative(pt, dataStorage) for pt in ptList])
        return polyline
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def ellipseToNative(poly: Ellipse, dataStorage) -> "QgsLineString":
    """Converts a Speckle Ellipse to QgsLineString"""
    try:
        try:
            angle = atan(poly.plane.xdir.y / poly.plane.xdir.x)
        except:
            angle = math.pi / 2

        ellipse = QgsEllipse(
            pointToNative(poly.plane.origin, dataStorage),
            poly.firstRadius,
            poly.secondRadius,
            angle,
        )
        ellipse = ellipse.toLineString()
        return ellipse
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def curveToNative(poly: Curve, dataStorage) -> "QgsLineString":
    """Converts a Speckle Curve to QgsLineString"""
    try:
        display = poly.displayValue
        curve = polylineToNative(display, dataStorage)
        return curve
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def arcToNative(poly: Arc, dataStorage) -> "QgsCircularString":
    """Converts a Speckle Arc to QgsCircularString"""
    try:
        arc = QgsCircularString(
            pointToNative(poly.startPoint, dataStorage),
            pointToNative(poly.midPoint, dataStorage),
            pointToNative(poly.endPoint, dataStorage),
        )
        return arc
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def circleToNative(poly: Circle, dataStorage) -> "QgsLineString":
    """Converts a Speckle Circle to QgsLineString"""
    try:
        scaleFactor = get_scale_factor(poly.units, dataStorage)
        circle = QgsCircle(
            pointToNative(poly.plane.origin, dataStorage), poly.radius * scaleFactor
        )
        circle = (
            circle.toLineString()
        )  # QgsCircle is not supported to be added as a feature, workaround (not working): https://gis.stackexchange.com/questions/411892/typeerror-qgsgeometry-frompolygonxy-argument-1-has-unexpected-type-qgspolyg
        return circle
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def polycurveToNative(poly: Polycurve, dataStorage) -> "QgsLineString":
    try:
        curve = QgsCompoundCurve()

        points = []
        singleSegm = 0
        try:
            if len(poly.segments) == 0:
                return None
            elif len(poly.segments) == 1:
                singleSegm = 1

            for segm in poly.segments:  # Line, Polyline, Curve, Arc, Circle
                if isinstance(segm, Line):
                    converted = lineToNative(segm, dataStorage)  # QgsLineString
                    if singleSegm == 1:
                        return converted
                elif isinstance(segm, Polyline):
                    converted = polylineToNative(segm, dataStorage)  # QgsLineString
                    if singleSegm == 1:
                        return converted
                elif isinstance(segm, Curve):
                    converted = curveToNative(segm, dataStorage)  # QgsLineString
                    if singleSegm == 1:
                        return converted
                elif isinstance(segm, Circle):
                    pts = [
                        pointToNative(pt, dataStorage)
                        for pt in speckleArcCircleToPoints(segm)
                    ]
                    converted = QgsLineString(pts)  # QgsLineString
                    if singleSegm == 1:
                        return circleToNative(segm, dataStorage)
                    else:
                        return None
                elif isinstance(segm, Arc):
                    converted = arcToNative(segm, dataStorage)
                    if singleSegm == 1:
                        return arcToNative(segm, dataStorage)
                elif isinstance(segm, Ellipse):
                    pts = [
                        pointToNative(pt, dataStorage)
                        for pt in speckleEllipseToPoints(segm, dataStorage)
                    ]
                    converted = QgsLineString(pts)  # QgsLineString
                    if singleSegm == 1:
                        return arcToNative(segm, dataStorage)
                    else:
                        return None
                else:  # return a part of the curve
                    logToUser(
                        f"Part of the polycurve cannot be converted",
                        level=1,
                        func=inspect.stack()[0][3],
                    )
                    curve = QgsLineString(points)
                    return curve

                # add converted segment
                if converted is not None:
                    curve.addCurve(converted, extendPrevious=True)
                else:
                    logToUser(
                        f"Part of the polycurve cannot be converted",
                        level=1,
                        func=inspect.stack()[0][3],
                    )
                    curve = QgsLineString(points)
                    return curve
        except:
            curve = None
        return curve

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def speckleEllipseToPoints(poly: Ellipse, dataStorage) -> List[Point]:
    try:
        qgsLineStr = ellipseToNative(poly, dataStorage)
        points = qgsLineStr.vertices()

        specklePts = [pointToSpeckle(pt, None, None, dataStorage) for pt in points]
        return specklePts
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return
