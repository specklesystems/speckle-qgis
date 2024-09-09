import earcut
import inspect
from math import cos, sin, atan
import math
import earcut.earcut
from specklepy.objects.geometry import (
    Point,
    Line,
    Polyline,
    Circle,
    Arc,
    Mesh,
    Polycurve,
    Vector,
)
from specklepy.objects import Base
from typing import Any, List, Tuple, Union, Dict

import geopandas as gpd
from geovoronoi import voronoi_regions_from_coords

try:
    from qgis.core import (
        QgsCoordinateTransform,
        Qgis,
        QgsPointXY,
        QgsGeometry,
        QgsRasterBandStats,
        QgsFeature,
        QgsFields,
        QgsField,
        QgsVectorLayer,
        QgsRasterLayer,
        QgsCoordinateReferenceSystem,
        QgsProject,
        QgsUnitTypes,
    )
except ModuleNotFoundError:
    pass

from speckle.utils.panel_logging import logToUser

import numpy as np


def cross_product(
    pt1: Union[List[float], Tuple[float]], pt2: Union[List[float], Tuple[float]]
) -> List[float]:
    if len(pt1) < 3 or len(pt2) < 3:
        raise ValueError(f"Not enough arguments for 3-dimentional point {pt1} or {pt2}")
    return [
        (pt1[1] * pt2[2]) - (pt1[2] * pt2[1]),
        (pt1[2] * pt2[0]) - (pt1[0] * pt2[2]),
        (pt1[0] * pt2[1]) - (pt1[1] * pt2[0]),
    ]


def dot(
    pt1: Union[List[float], Tuple[float]], pt2: Union[list[float], Tuple[float]]
) -> float:
    if len(pt1) < 3 or len(pt2) < 3:
        raise ValueError(f"Not enough arguments for 3-dimentional point {pt1} or {pt2}")
    return (pt1[0] * pt2[0]) + (pt1[1] * pt2[1]) + (pt1[2] * pt2[2])


def normalize(pt: Union[List[float], Tuple[float]], tolerance=1e-10) -> List[float]:
    magnitude = dot(pt, pt) ** 0.5
    if abs(magnitude - 1) < tolerance:
        return pt

    if magnitude != 0:
        scale = 1.0 / magnitude
    else:
        scale = 1.0
    normalized_vector = [coordinate * scale for coordinate in pt]
    return normalized_vector


def createPlane(
    pt1: Union[List[float], Tuple[float]],
    pt2: Union[List[float], Tuple[float]],
    pt3: Union[List[float], Tuple[float]],
) -> dict:
    if len(pt1) < 3 or len(pt2) < 3 or len(pt3) < 3:
        raise ValueError(
            f"Not enough arguments for 3-dimentional point {pt1}, {pt2} or {pt3}"
        )
    vector1to2 = [pt2[0] - pt1[0], pt2[1] - pt1[1], pt2[2] - pt1[2]]
    vector1to3 = [pt3[0] - pt1[0], pt3[1] - pt1[1], pt3[2] - pt1[2]]

    u_direction = normalize(vector1to2)
    normal = cross_product(u_direction, vector1to3)
    return {"origin": pt1, "normal": normal}


def project_to_plane_on_z(
    point: Union[List[float], Tuple[float]], plane: Dict
) -> float:
    if len(point) < 2 or "normal" not in plane.keys() or "origin" not in plane.keys():
        raise ValueError(f"Invalid arguments for a point {point} or a plane {plane}")
    if plane["normal"][2] == 0:
        raise ValueError(f"Invalid arguments for a point {point} or a plane {plane}")

    d = dot(plane["normal"], plane["origin"])
    z_value_on_plane = (
        d - (plane["normal"][0] * point[0]) - (plane["normal"][1] * point[1])
    ) / plane["normal"][2]
    return z_value_on_plane


def projectToPolygon(
    point: Union[List[float], Tuple[float]],
    polygonPts: List[List[float]],
) -> float:
    if len(point) < 2:
        raise ValueError(f"Not enough arguments for a point {point}")
    if len(polygonPts) < 3:
        return 0
    pt1 = polygonPts[0]
    pt2 = polygonPts[1]
    pt3 = polygonPts[2]
    plane = createPlane(pt1, pt2, pt3)
    z = project_to_plane_on_z(point, plane)

    if z == -0.0:
        z = 0
    return z


def getPolyPtsSegments(
    geom: Any, dataStorage: "DataStorage", coef: Union[int, None] = None, xform=None
):
    vertices = []
    vertices3d = []
    segmList = []
    holes = []
    if xform is not None:
        geom.transform(xform)
    try:
        extRing = geom.exteriorRing()
        pt_iterator = extRing.vertices()
    except:
        try:
            extRing = geom.constGet().exteriorRing()
            pt_iterator = extRing.vertices()
        except:
            pt_iterator = geom.vertices()

    # get boundary points and segments
    pointListLocalOuter = []
    startLen = len(vertices)
    for i, pt in enumerate(pt_iterator):
        if (
            len(pointListLocalOuter) > 0
            and pt.x() == pointListLocalOuter[0].x()
            and pt.y() == pointListLocalOuter[0].y()
        ):
            # don't repeat 1st point
            pass
        elif coef is None:
            pointListLocalOuter.append(pt)
        else:
            if i % coef == 0:
                pointListLocalOuter.append(pt)
            else:
                # don't add points, which are in-between specified step (coeff)
                # e.g. if coeff=5, we skip ponts 1,2,3,4, but add points 0 and 5
                pass

    for i, pt in enumerate(pointListLocalOuter):
        x, y = apply_pt_offsets_rotation_on_send(pt.x(), pt.y(), dataStorage)
        vertices.append([x, y])
        try:
            vertices3d.append([x, y, pt.z()])
        except:
            vertices3d.append([x, y, 0])

        if i > 0:
            segmList.append([startLen + i - 1, startLen + i])

    # get voids points and segments
    try:
        geom = geom.constGet()
    except:
        pass
    try:
        intRingsNum = geom.numInteriorRings()

        for k in range(intRingsNum):
            intRing = geom.interiorRing(k)
            pt_iterator = intRing.vertices()

            pt_list = list(pt_iterator)
            pointListLocal = []
            startLen = len(vertices)

            for i, pt in enumerate(pt_list):
                if (
                    len(pointListLocal) > 0
                    and pt.x() == pointListLocal[0].x()
                    and pt.y() == pointListLocal[0].y()
                ):
                    # don't repeat 1st point
                    continue
                elif pt not in pointListLocalOuter:
                    # make sure it's not already included in the outer part of geometry

                    if coef is None or len(pt_list) / coef < 5:
                        # coef was calculated by the outer ring.
                        # We need to make sure inner ring will have at least 4 points, otherwise ignore coeff.
                        pointListLocal.append(pt)
                    else:
                        if i % coef == 0:
                            pointListLocal.append(pt)
                        else:
                            # don't add points, which are in-between specified step (coeff)
                            # e.g. if coeff=5, we skip ponts 1,2,3,4, but add points 0 and 5
                            pass

            if len(pointListLocal) > 2:
                holes.append(
                    [
                        apply_pt_offsets_rotation_on_send(p.x(), p.y(), dataStorage)
                        for p in pointListLocal
                    ]
                )
            for i, pt in enumerate(pointListLocal):
                x, y = apply_pt_offsets_rotation_on_send(pt.x(), pt.y(), dataStorage)
                try:
                    vertices3d.append([x, y, pt.z()])
                except:
                    vertices3d.append([x, y, None])

                if i > 0:
                    segmList.append([startLen + i - 1, startLen + i])
    except Exception as e:
        logToUser(e, level=1, func=inspect.stack()[0][3])
        raise e
    return vertices, vertices3d, segmList, holes


def triangulatePolygon(
    vertices: Any,
    holes: Any,
    dimensions: int,
    dataStorage: "DataStorage",
    coef: Union[int, None] = None,
    xform=None,
) -> Tuple[dict, Union[List[List[float]], None], int]:
    try:
        # import triangle as tr
        # vertices = []  # only outer
        # holes = []
        # pack = getPolyPtsSegments(geom, dataStorage, coef, xform)

        # close the loop
        r"""
        if len(vertices) > 0:
            vertices.extend(vertices[:dimensions])
        for i, _ in enumerate(holes):
            if len(holes[i]) > 0:
                holes[i].extend(holes[i][:dimensions])
        """

        if len(holes) == 0:
            holes = None

        try:
            triangles = earcut.earcut.earcut(vertices, holes, dim=dimensions)
            triangle_tuples = [
                (triangles[3 * i], triangles[3 * i + 1], triangles[3 * i + 2])
                for i, _ in enumerate(triangles)
                if i < len(triangles) / 3
            ]
            # return_dict = {
            #    "vertices": vertices,
            #    "triangles": triangle_tuples,
            # }
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])
            return None
        return triangle_tuples

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def trianglateQuadMesh(mesh: Mesh) -> Union[Mesh, None]:
    new_mesh = None
    try:
        new_v: List[float] = []
        new_f: List[int] = []
        new_c: List[int] = []

        # fill new color and vertices lists
        if mesh.colors is not None:
            used_ind_colors = []
            for i, _ in enumerate(mesh.colors):
                try:
                    if i not in used_ind_colors:
                        new_c.extend(
                            [
                                mesh.colors[i],
                                mesh.colors[i + 1],
                                mesh.colors[i + 2],
                                mesh.colors[i + 2],
                                mesh.colors[i + 3],
                                mesh.colors[i],
                            ]
                        )
                        used_ind_colors.extend([i, i + 1, i + 2, i + 3])
                except Exception as e:
                    print(e)

        used_ind_vertex = []
        for i, v in enumerate(mesh.vertices):
            try:
                if i not in used_ind_vertex:
                    v0 = [mesh.vertices[i], mesh.vertices[i + 1], mesh.vertices[i + 2]]
                    v1 = [
                        mesh.vertices[i + 3],
                        mesh.vertices[i + 4],
                        mesh.vertices[i + 5],
                    ]
                    v2 = [
                        mesh.vertices[i + 6],
                        mesh.vertices[i + 7],
                        mesh.vertices[i + 8],
                    ]
                    v3 = [
                        mesh.vertices[i + 9],
                        mesh.vertices[i + 10],
                        mesh.vertices[i + 11],
                    ]

                    new_v.extend(v0 + v1 + v2 + v2 + v3 + v0)
                    new_f.extend(
                        [
                            int(3),
                            int(i / 12),
                            int(i / 12) + 1,
                            int(i / 12) + 2,
                            int(3),
                            int(i / 12) + 3,
                            int(i / 12) + 4,
                            int(i / 12) + 5,
                        ]
                    )
                    used_ind_vertex.extend(list(range(i, i + 12)))
            except Exception as e:
                print(e)
        new_mesh = Mesh.create(new_v, new_f, new_c)
        new_mesh.units = mesh.units
    except Exception as e:
        print(e)
        return None
    return new_mesh


def fix_orientation(
    polyBorder: List[Union[Point, "QgsPoint"]], positive: bool = True, coef: int = 1
) -> List[Union[Point, "QgsPoint"]]:
    sum_orientation = 0
    for k, _ in enumerate(polyBorder):
        index = k + 1
        if k == len(polyBorder) - 1:
            index = 0

        try:
            pt = polyBorder[k * coef]
            pt2 = polyBorder[index * coef]

            if isinstance(pt, Point) and isinstance(pt2, Point):
                sum_orientation += (pt2.x - pt.x) * (pt2.y + pt.y)  # if Speckle Points
            else:
                sum_orientation += (pt2.x() - pt.x()) * (
                    pt2.y() + pt.y()
                )  # if QGIS Points
        except IndexError:
            break

    if positive is True:
        if sum_orientation < 0:
            polyBorder.reverse()
    else:
        if sum_orientation > 0:
            polyBorder.reverse()
    return polyBorder


def getHolePt(pointListLocal: List[Union[Point, "QgsPoint"]]) -> List[float]:
    pointListLocal = fix_orientation(pointListLocal, True, 1)
    minXpt = pointListLocal[0]
    index = 0
    index2 = 1
    points_as_speckle = isinstance(minXpt, Point)
    for i, pt in enumerate(pointListLocal):
        if points_as_speckle:
            check_next = pt.x < minXpt.x  # if Speckle points
        else:
            check_next = pt.x() < minXpt.x()

        if check_next:
            minXpt = pt
            index = i
            if i == len(pointListLocal) - 1:
                index2 = 0
            else:
                index2 = index + 1
    if points_as_speckle:
        x_range = pointListLocal[index2].x - minXpt.x
        y_range = pointListLocal[index2].y - minXpt.y
        if y_range > 0:
            sidePt = [minXpt.x + abs(x_range / 2) + 0.001, minXpt.y + y_range / 2]
        else:
            sidePt = [minXpt.x + abs(x_range / 2) - 0.001, minXpt.y + y_range / 2]

    else:
        x_range = pointListLocal[index2].x - minXpt.x
        y_range = pointListLocal[index2].y - minXpt.y
        if y_range > 0:
            sidePt = [minXpt.x() + abs(x_range / 2) + 0.001, minXpt.y() + y_range / 2]
        else:
            sidePt = [minXpt.x() + abs(x_range / 2) - 0.001, minXpt.y() + y_range / 2]
    return sidePt


def getArcAngles(poly: Arc, dataStorage) -> Tuple[Union[float, None]]:
    try:
        if poly.startPoint.x == poly.plane.origin.x:
            angle1 = math.pi / 2
        else:
            angle1 = atan(
                abs(
                    (poly.startPoint.y - poly.plane.origin.y)
                    / (poly.startPoint.x - poly.plane.origin.x)
                )
            )  # between 0 and pi/2

        if (
            poly.plane.origin.x < poly.startPoint.x
            and poly.plane.origin.y > poly.startPoint.y
        ):
            angle1 = 2 * math.pi - angle1
        if (
            poly.plane.origin.x > poly.startPoint.x
            and poly.plane.origin.y > poly.startPoint.y
        ):
            angle1 = math.pi + angle1
        if (
            poly.plane.origin.x > poly.startPoint.x
            and poly.plane.origin.y < poly.startPoint.y
        ):
            angle1 = math.pi - angle1

        if poly.endPoint.x == poly.plane.origin.x:
            angle2 = math.pi / 2
        else:
            angle2 = atan(
                abs(
                    (poly.endPoint.y - poly.plane.origin.y)
                    / (poly.endPoint.x - poly.plane.origin.x)
                )
            )  # between 0 and pi/2

        if (
            poly.plane.origin.x < poly.endPoint.x
            and poly.plane.origin.y > poly.endPoint.y
        ):
            angle2 = 2 * math.pi - angle2
        if (
            poly.plane.origin.x > poly.endPoint.x
            and poly.plane.origin.y > poly.endPoint.y
        ):
            angle2 = math.pi + angle2
        if (
            poly.plane.origin.x > poly.endPoint.x
            and poly.plane.origin.y < poly.endPoint.y
        ):
            angle2 = math.pi - angle2

        return angle1, angle2
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None


def getArcRadianAngle(arc: Arc, dataStorage) -> List[float]:
    try:
        interval = None
        normal = arc.plane.normal.z
        angle1, angle2 = getArcAngles(arc, dataStorage)
        if angle1 is None or angle2 is None:
            return None
        interval = abs(angle2 - angle1)

        if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1):
            pass
        if angle1 > angle2 and normal == 1:
            interval = abs((2 * math.pi - angle1) + angle2)
        if angle2 > angle1 and normal == -1:
            interval = abs((2 * math.pi - angle2) + angle1)
        return interval, angle1, angle2
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None, None


def speckleArcCircleToPoints(poly: Union[Arc, Circle], dataStorage) -> List[Point]:
    try:
        points = []
        if poly.plane is None or poly.plane.normal.z == 0:
            normal = 1
        else:
            normal = poly.plane.normal.z

        if isinstance(poly, Circle):
            interval = 2 * math.pi
            range_start = 0
            angle1 = 0

        elif isinstance(poly, Arc):
            points.append(poly.startPoint)
            range_start = 0

            interval, angle1, angle2 = getArcRadianAngle(poly, dataStorage)

            if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1):
                pass
            if angle1 > angle2 and normal == 1:
                interval = abs((2 * math.pi - angle1) + angle2)
            if angle2 > angle1 and normal == -1:
                interval = abs((2 * math.pi - angle2) + angle1)

        pointsNum = math.floor(abs(interval)) * 12
        if pointsNum < 4:
            pointsNum = 4

        for i in range(range_start, pointsNum + 1):
            k = i / pointsNum  # to reset values from 1/10 to 1
            angle = angle1 + k * interval * normal

            pt = Point(
                x=poly.plane.origin.x + poly.radius * cos(angle),
                y=poly.plane.origin.y + poly.radius * sin(angle),
                z=0,
            )

            pt.units = poly.plane.origin.units
            points.append(pt)

        if isinstance(poly, Arc):
            points.append(poly.endPoint)
        return points
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return []


def specklePolycurveToPoints(poly: Polycurve, dataStorage) -> List[Point]:
    try:
        points = []
        if poly.segments is None:
            return []
        for i, segm in enumerate(poly.segments):
            pts = []
            if isinstance(segm, Arc) or isinstance(segm, Circle):
                pts: List[Point] = speckleArcCircleToPoints(segm, dataStorage)
            elif isinstance(segm, Line):
                pts: List[Point] = [segm.start, segm.end]
            elif isinstance(segm, Polyline):
                pts: List[Point] = segm.as_points()

            if i == 0:
                points.extend(pts)
            else:
                points.extend(pts[1:])
        return points
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return []


def speckleBoundaryToSpecklePts(
    boundary: Union[Circle, Arc, Line, Polycurve, Polyline], dataStorage
) -> List[Point]:
    # add boundary points
    try:
        polyBorder = []
        if isinstance(boundary, Circle) or isinstance(boundary, Arc):
            polyBorder = speckleArcCircleToPoints(boundary, dataStorage)
        elif isinstance(boundary, Polycurve):
            polyBorder = specklePolycurveToPoints(boundary, dataStorage)
        elif isinstance(boundary, Line):
            pass
        else:
            try:
                polyBorder = boundary.as_points()
            except:
                pass  # if Line or None
        for i, p in enumerate(polyBorder):
            if polyBorder[i].z == -0.0 or math.isnan(polyBorder[i].z):
                polyBorder[i].z = 0
        return polyBorder
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return []


def addCorrectUnits(geom: Base, dataStorage) -> Base:
    if not isinstance(geom, Base):
        return None
    units = dataStorage.currentUnits

    geom.units = units
    if isinstance(geom, Arc):
        geom.plane.origin.units = units
        geom.startPoint.units = units
        geom.midPoint.units = units
        geom.endPoint.units = units

    elif isinstance(geom, Polycurve):
        for s in geom.segments:
            s.units = units
            if isinstance(s, Arc):
                s.plane.origin.units = units
                s.startPoint.units = units
                s.midPoint.units = units
                s.endPoint.units = units

    return geom


def getArcNormal(poly: Arc, midPt: Point, dataStorage) -> Union[Vector, None]:
    try:
        angle1, angle2 = getArcAngles(poly, dataStorage)

        if midPt.x == poly.plane.origin.x:
            angle = math.pi / 2
        else:
            angle = atan(
                abs((midPt.y - poly.plane.origin.y) / (midPt.x - poly.plane.origin.x))
            )  # between 0 and pi/2

        if poly.plane.origin.x < midPt.x and poly.plane.origin.y > midPt.y:
            angle = 2 * math.pi - angle
        if poly.plane.origin.x > midPt.x and poly.plane.origin.y > midPt.y:
            angle = math.pi + angle
        if poly.plane.origin.x > midPt.x and poly.plane.origin.y < midPt.y:
            angle = math.pi - angle

        normal = Vector()
        normal.x = normal.y = 0

        if angle1 > angle > angle2:
            normal.z = -1
        if angle1 > angle2 > angle:
            normal.z = 1

        if angle2 > angle1 > angle:
            normal.z = -1
        if angle > angle1 > angle2:
            normal.z = 1

        if angle2 > angle > angle1:
            normal.z = 1
        if angle > angle2 > angle1:
            normal.z = -1

        return normal
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def apply_pt_offsets_rotation_on_send(
    x: float, y: float, dataStorage
) -> Tuple[float, float]:  # on Send
    try:
        offset_x = dataStorage.crs_offset_x
        offset_y = dataStorage.crs_offset_y
        rotation = dataStorage.crs_rotation
        if offset_x == offset_y == rotation == 0:
            return x, y
        if offset_x is None and offset_y is None and rotation is None:
            return x, y

        if offset_x is not None and isinstance(offset_x, float):
            x -= offset_x
        if offset_y is not None and isinstance(offset_y, float):
            y -= offset_y
        if (
            rotation is not None
            and (isinstance(rotation, float) or isinstance(rotation, int))
            and -360 < rotation < 360
        ):
            a = rotation * math.pi / 180
            x2 = x * math.cos(a) + y * math.sin(a)
            y2 = -x * math.sin(a) + y * math.cos(a)
            x = x2
            y = y2
        return x, y
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        raise e


def transform_speckle_pt_on_receive(pt_original: Point, dataStorage) -> Point:
    offset_x = dataStorage.crs_offset_x
    offset_y = dataStorage.crs_offset_y
    rotation = dataStorage.crs_rotation

    pt = Point(
        x=pt_original.x, y=pt_original.y, z=pt_original.z, units=pt_original.units
    )

    gisLayer = None
    try:
        gisLayer = dataStorage.latestHostApp.lower().endswith("gis")
        applyTransforms = False if (gisLayer and gisLayer is True) else True
    except Exception as e:
        print(e)
        applyTransforms = True

    # for non-GIS layers
    if applyTransforms is True:
        if (
            rotation is not None
            and (isinstance(rotation, float) or isinstance(rotation, int))
            and -360 < rotation < 360
        ):
            a = rotation * math.pi / 180
            x2 = pt.x
            y2 = pt.y

            # if a > 0: # turn counterclockwise on receive
            x2 = pt.x * math.cos(a) - pt.y * math.sin(a)
            y2 = pt.x * math.sin(a) + pt.y * math.cos(a)

            pt.x = x2
            pt.y = y2
        if (
            offset_x is not None
            and isinstance(offset_x, float)
            and offset_y is not None
            and isinstance(offset_y, float)
        ):
            pt.x += offset_x
            pt.y += offset_y

    # for GIS layers
    if gisLayer is True:
        try:
            offset_x = dataStorage.current_layer_crs_offset_x
            offset_y = dataStorage.current_layer_crs_offset_y
            rotation = dataStorage.current_layer_crs_rotation

            if (
                rotation is not None
                and isinstance(rotation, float)
                and -360 < rotation < 360
            ):
                a = rotation * math.pi / 180
                x2 = pt.x
                y2 = pt.y

                # if a > 0: # turn counterclockwise on receive
                x2 = pt.x * math.cos(a) - pt.y * math.sin(a)
                y2 = pt.x * math.sin(a) + pt.y * math.cos(a)

                pt.x = x2
                pt.y = y2
            if (
                offset_x is not None
                and isinstance(offset_x, float)
                and offset_y is not None
                and isinstance(offset_y, float)
            ):
                pt.x += offset_x
                pt.y += offset_y
        except Exception as e:
            print(e)

    return pt


def apply_pt_transform_matrix(pt: Point, dataStorage) -> Point:
    try:
        if dataStorage.matrix is not None:
            b = np.matrix([pt.x, pt.y, pt.z, 1])
            res = b * dataStorage.matrix
            x, y, z = res.item(0), res.item(1), res.item(2)
            return Point(x=x, y=y, z=z, units=pt.units)
    except Exception as e:
        print(e)
    return pt


def apply_feature_crs_transform(f, sourceCRS, targetCRS, dataStorage):
    if sourceCRS != targetCRS:
        xform = QgsCoordinateTransform(sourceCRS, targetCRS, dataStorage.project)
        geometry = f.geometry()
        geometry.transform(xform)
        f.setGeometry(geometry)
    return f


def apply_qgis_geometry_crs_transform(geometry, sourceCRS, targetCRS, dataStorage):
    if sourceCRS != targetCRS:
        xform = QgsCoordinateTransform(sourceCRS, targetCRS, dataStorage.project)
        geometry.transform(xform)
    return geometry
