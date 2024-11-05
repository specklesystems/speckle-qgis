""" This module contains all geometry conversion functionality To and From Speckle."""

import inspect
import math
import random

from speckle.converter.geometry import transform

try:
    from qgis.core import (
        QgsGeometry,
        QgsAbstractGeometry,
        QgsPolygon,
        QgsPointXY,
        QgsFeature,
        QgsVectorLayer,
        QgsCoordinateReferenceSystem,
    )
except ModuleNotFoundError:
    pass

from typing import List, Union

from specklepy.objects.geometry import Point, Line, Polyline, Arc, Polycurve
from specklepy.objects import Base
from specklepy.objects.GIS.geometry import GisPolygonGeometry

from speckle.converter.geometry.mesh import meshPartsFromPolygon, constructMesh
from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
    unknownLineToSpeckle,
)
from speckle.converter.geometry.utils import (
    projectToPolygon,
    speckleBoundaryToSpecklePts,
)

# from speckle.converter.geometry.utils import *
from speckle.converter.layers.utils import (
    get_raster_stats,
    getArrayIndicesFromXY,
    getElevationLayer,
    getRasterArrays,
    moveVertically,
    reprojectPt,
)
from speckle.utils.panel_logging import logToUser

import numpy as np


def polygonToSpeckleMesh(
    geom: "QgsGeometry",
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    dataStorage,
    xform=None,
):

    try:
        vertices = []
        faces = []
        colors = []
        existing_vert = 0
        boundary = None
        for p in geom.parts():
            boundary, voidsNative = getPolyBoundaryVoids(p, feature, layer, dataStorage)
            polyBorder = speckleBoundaryToSpecklePts(boundary, dataStorage)
            if len(polyBorder) < 3:
                continue
            voids = []
            voidsAsPts = []

            for v_speckle in voidsNative:
                pts_fixed = []
                # v_speckle = unknownLineToSpeckle(v, True, feature, layer, dataStorage)
                pts = speckleBoundaryToSpecklePts(v_speckle, dataStorage)

                plane_pts = [
                    [polyBorder[0].x, polyBorder[0].y, polyBorder[0].z],
                    [polyBorder[1].x, polyBorder[1].y, polyBorder[1].z],
                    [polyBorder[2].x, polyBorder[2].y, polyBorder[2].z],
                ]
                for pt in pts:
                    z_val = pt.z
                    # print(str(z_val))
                    # project the pts on the plane
                    point = [pt.x, pt.y, 0]
                    z_val = projectToPolygon(point, plane_pts)
                    if math.isnan(z_val):
                        z_val = 0
                    pts_fixed.append(Point(units="m", x=pt.x, y=pt.y, z=z_val))

                voids.append(
                    polylineFromVerticesToSpeckle(
                        pts_fixed, True, feature, layer, dataStorage
                    )
                )
                voidsAsPts.append(pts_fixed)
            (
                total_vert,
                vertices_x,
                faces_x,
                colors_x,
                iterations,
            ) = meshPartsFromPolygon(
                polyBorder,
                voidsAsPts,
                existing_vert,
                feature,
                p,
                layer,
                None,
                dataStorage,
                xform,
            )

            if total_vert is None:
                return None
            existing_vert += total_vert
            vertices.extend(vertices_x)
            faces.extend(faces_x)
            colors.extend(colors_x)

        mesh = constructMesh(vertices, faces, colors, dataStorage)
        if mesh is not None:
            polygon = GisPolygonGeometry(units="m")
            # polygon.units = "m"
            # polygon.displayValue = [mesh]
            # polygon.boundary = None
            # polygon.voids = None
        else:
            polygon = GisPolygonGeometry(units="m", boundary=boundary, voids=voids)
            # polygon.boundary = boundary
            # polygon.voids = voids
            logToUser(
                "Mesh creation from Polygon failed. Boundaries will be used as displayValue",
                level=1,
                func=inspect.stack()[0][3],
            )
        return polygon

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def getZaxisTranslation(layer, boundaryPts, dataStorage):
    #### check if elevation is applied and layer exists:
    elevationLayer = getElevationLayer(dataStorage)
    translationValue = None

    min_z = min([p.z() for p in boundaryPts])
    if math.isnan(min_z):
        min_z = 0

    if elevationLayer is not None:
        all_arrays, all_mins, all_maxs, all_na = getRasterArrays(elevationLayer)
        settings_elevation_layer = get_raster_stats(elevationLayer)
        allElevations = []
        for pt in boundaryPts:
            # posX, posY = reprojectPt(
            #    pt.x(), pt.y(), polygonWkt, polygonProj, rasterWkt, rasterProj
            # )
            reprojected_pt = transform.transform(
                dataStorage.project,
                QgsPointXY(pt.x(), pt.y()),
                layer.crs(),
                elevationLayer.crs(),
            )
            posX = reprojected_pt.x()
            posY = reprojected_pt.y()
            index1, index2, remainder1, remainder2 = getArrayIndicesFromXY(
                settings_elevation_layer, posX, posY
            )
            # print("___finding elevation__")
            # print(posX)
            # print(index1)

            if index1 is None:
                continue
            else:
                h = all_arrays[0][index1][index2]
                allElevations.append(h)

        if len(allElevations) == 0:
            translationValue = None
        else:
            if np.isnan(boundaryPts[0].z()):  # for flat polygons with z=0
                translationValue = min(allElevations)
            else:
                translationValue = min(allElevations) - min_z
    else:
        translationValue = -1 * min_z

    return translationValue


def isFlat(ptList):
    flat = True
    universal_z_value = ptList[0].z()
    for i, pt in enumerate(ptList):
        if isinstance(pt, QgsPointXY):
            break
        elif np.isnan(pt.z()):
            break
        elif pt.z() != universal_z_value:
            flat = False
            break
    return flat


def polygonToSpeckle(
    geom_original: "QgsAbstractGeometry",
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    height,
    projectZval,
    dataStorage,
    xform=None,
):
    """Converts a QgsPolygon to Speckle"""

    iterations = 0
    try:
        geom = geom_original.clone()
        boundary, voidsNative = getPolyBoundaryVoids(
            geom, feature, layer, dataStorage, xform
        )

        if projectZval is not None:
            boundary = moveVertically(boundary, projectZval)

        polyBorder = speckleBoundaryToSpecklePts(boundary, dataStorage)
        if len(polyBorder) < 3:
            return None, None
        voids = []
        voidsAsPts = []

        for v_speckle in voidsNative:
            pts_fixed = []
            pts = speckleBoundaryToSpecklePts(v_speckle, dataStorage)

            plane_pts = [
                [polyBorder[0].x, polyBorder[0].y, polyBorder[0].z],
                [polyBorder[1].x, polyBorder[1].y, polyBorder[1].z],
                [polyBorder[2].x, polyBorder[2].y, polyBorder[2].z],
            ]
            for pt in pts:
                z_val = pt.z
                # print(str(z_val))
                # project the pts on the plane
                point = [pt.x, pt.y, 0]
                z_val = projectToPolygon(point, plane_pts)
                pts_fixed.append(Point(units="m", x=pt.x, y=pt.y, z=z_val))

            voids.append(
                polylineFromVerticesToSpeckle(
                    pts_fixed, True, feature, layer, dataStorage
                )
            )
            voidsAsPts.append(pts_fixed)

        polygon = GisPolygonGeometry(units="m", boundary=boundary, voids=voids)
        iterations, vertices, faces, colors, iterations = meshPartsFromPolygon(
            polyBorder, voidsAsPts, 0, feature, geom, layer, height, dataStorage, xform
        )

        mesh = constructMesh(vertices, faces, colors, dataStorage)
        if mesh is not None:
            polygon.displayValue = [mesh]
            # polygon["baseGeometry"] = mesh
            # https://latest.speckle.systems/projects/85bc4f61c6/models/6cd9058fba@2a5d23a277
            # https://speckle.community/t/revit-add-new-parameters/5170/2
        else:
            polygon.displayValue = []
            logToUser(
                "Mesh creation from Polygon failed. Boundaries will be used as displayValue",
                level=1,
                func=inspect.stack()[0][3],
            )

        return polygon, iterations

    except Exception as e:
        logToUser(
            "Some polygons might be invalid: " + str(e),
            level=1,
            func=inspect.stack()[0][3],
        )
        return None, None


def hatchToNative(hatch: Base, dataStorage):
    """Convert Hatch to QGIS Polygon."""

    polygon = QgsPolygon()
    try:
        loops: list = hatch["loops"]
        boundary = None
        voids = []
        for loop in loops:
            if len(loops) == 1 or loop["Type"] == 1:  # Outer
                boundary = loop["Curve"]
            else:
                voids.append(loop["Curve"])
        if boundary is None:
            logToUser("Invalid Hatch outer loop", level=2, func=inspect.stack()[0][3])
            return polygon
        polygon.setExteriorRing(polylineToNative(boundary, dataStorage))

        for void in voids:
            polygon.addInteriorRing(polylineToNative(void, dataStorage))

        return polygon
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return polygon


def polygonToNative(poly: Base, dataStorage) -> "QgsPolygon":
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""

    polygon = QgsPolygon()
    try:
        # boundary
        try:  # if it's indeed a polygon with QGIS properties
            boundary = poly.boundary
        except:
            try:
                boundary = poly["boundary"]
            except:
                return None

        if boundary is None:
            logToUser(
                f"Polygon has no valid boundary", level=2, func=inspect.stack()[0][3]
            )
            return None
        polygon.setExteriorRing(polylineToNative(boundary, dataStorage))

        # voids
        try:
            voids = poly.voids
        except:
            try:
                voids = poly["voids"]
            except:
                pass

        for void in voids:
            if void is None:
                logToUser(
                    f"Polygon interior ring is invalid and will be skipped",
                    level=1,
                    func=inspect.stack()[0][3],
                )
            else:
                polygon.addInteriorRing(polylineToNative(void, dataStorage))

        return polygon
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return polygon


def getPolyBoundaryVoids(
    geom_original: "QgsGeometry",
    feature: "QgsFeature",
    layer: "QgsVectorLayer",
    dataStorage,
    xform=None,
):
    boundary = None
    voids: List[Union[None, Polyline, Arc, Line, Polycurve]] = []
    try:
        pt_iterator = []
        extRing = None

        if isinstance(geom_original, QgsGeometry):
            geom_original = geom_original.constGet()
        geom = geom_original.clone()

        try:
            extRing = geom.exteriorRing()
            pt_iterator = extRing.vertices()
        except:
            extRing = geom
            pt_iterator = geom.vertices()
        # for pt in pt_iterator:
        #     pointList.append(pt)
        if extRing is not None:
            boundary = unknownLineToSpeckle(
                extRing, True, feature, layer, dataStorage, xform
            )
        else:
            return boundary, voids

        # get voids
        for i in range(geom.numInteriorRings()):
            intRing = unknownLineToSpeckle(
                geom.interiorRing(i), True, feature, layer, dataStorage, xform
            )
            voids.append(intRing)

        return boundary, voids

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None
