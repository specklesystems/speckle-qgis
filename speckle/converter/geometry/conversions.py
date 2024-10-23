from specklepy.objects.GIS.geometry import (
    GisLineElement,
    GisPointElement,
    GisPolygonElement,
)

from typing import List, Sequence, Tuple, Union
import inspect

try:
    from qgis.core import (
        QgsGeometry,
        QgsWkbTypes,
        QgsMultiPoint,
        QgsAbstractGeometry,
        QgsMultiLineString,
        QgsMultiPolygon,
        QgsCircularString,
        QgsLineString,
        QgsRasterLayer,
        QgsVectorLayer,
        QgsFeature,
        QgsUnitTypes,
        QgsCoordinateTransform,
    )
except ModuleNotFoundError:
    pass

from speckle.converter.features.utils import getPolygonFeatureHeight
from speckle.converter.geometry.mesh import meshToNative
from speckle.converter.geometry.point import pointToNative, pointToSpeckle
from speckle.converter.geometry.polygon import (
    polygonToSpeckleMesh,
    getZaxisTranslation,
    isFlat,
    polygonToSpeckle,
    polygonToNative,
)
from speckle.converter.geometry.polyline import (
    compoudCurveToSpeckle,
    anyLineToSpeckle,
    polylineToSpeckle,
    arcToSpeckle,
    lineToNative,
    polylineToNative,
    ellipseToNative,
    curveToNative,
    arcToNative,
    circleToNative,
    polycurveToNative,
)
from speckle.converter.geometry.utils import addCorrectUnits

from specklepy.objects import Base
from specklepy.objects.geometry import (
    Line,
    Mesh,
    Point,
    Polyline,
    Curve,
    Arc,
    Circle,
    Ellipse,
    Polycurve,
)
from specklepy.objects.GIS.geometry import GisPolygonGeometry

from speckle.utils.panel_logging import logToUser
from speckle.converter.layers.utils import (
    getElevationLayer,
    isAppliedLayerTransformByKeywords,
)


def convertToSpeckle(
    feature: "QgsFeature", layer: "QgsVectorLayer" or "QgsRasterLayer", dataStorage
) -> Tuple[Union[Base, Sequence[Base], None], Union[int, None]]:
    """Converts the provided layer feature to Speckle objects"""
    try:
        iterations = 0
        sourceCRS = layer.crs()
        targetCRS = dataStorage.project.crs()
        xform = None
        if sourceCRS != targetCRS:
            xform = QgsCoordinateTransform(sourceCRS, targetCRS, dataStorage.project)

        geom_original: Union[QgsGeometry, QgsAbstractGeometry] = feature.geometry()

        geomSingleType = QgsWkbTypes.isSingleType(geom_original.wkbType())
        geomType = geom_original.type()

        if isinstance(geom_original, QgsGeometry):
            geom: QgsAbstractGeometry = geom_original.constGet()
        else:
            geom = geom_original

        # type = geom.wkbType()
        units = (
            dataStorage.currentUnits
        )  # QgsUnitTypes.encodeUnit(dataStorage.project.crs().mapUnits())

        if geomType == QgsWkbTypes.PointGeometry:
            # the geometry type can be of single or multi type
            if xform is not None:
                geom.transform(xform)
            if geomSingleType:
                result = pointToSpeckle(geom, feature, layer, dataStorage)
                result.units = units
                result = [result]
            else:
                result = [
                    pointToSpeckle(pt, feature, layer, dataStorage)
                    for pt in geom.parts()
                ]
                for r in result:
                    r.units = units

            element = GisPointElement(units=units, geometry=result)
            return element, iterations

        elif geomType == QgsWkbTypes.LineGeometry:  # 1
            if geomSingleType:
                result = anyLineToSpeckle(geom, feature, layer, dataStorage, xform)
                result = addCorrectUnits(result, dataStorage)
                result = [result]
                # return result
            else:
                result = [
                    anyLineToSpeckle(poly, feature, layer, dataStorage, xform)
                    for poly in geom.parts()
                ]
                for r in result:
                    r = addCorrectUnits(r, dataStorage)

            element = GisLineElement(units=units, geometry=result)
            return element, iterations

        # check if the layer was received from Mesh originally, don't apply Transformations
        elif (
            geomType == QgsWkbTypes.PolygonGeometry
            and not geomSingleType
            and layer.name().endswith("_as_Mesh")
            and "Speckle_ID" in layer.fields().names()
        ):
            if xform is not None:
                geom.transform(xform)
            result = polygonToSpeckleMesh(geom, feature, layer, dataStorage, None)
            if result is None:
                return None, None
            result.units = units
            for v in result.displayValue:
                if v is not None:
                    v.units = units

            if not isinstance(result, List):
                result = [result]
            element = GisPolygonElement(units=units, geometry=result)
            return element, iterations

        elif geomType == QgsWkbTypes.PolygonGeometry:  # 2
            height = getPolygonFeatureHeight(feature, layer, dataStorage)
            elevationLayer = getElevationLayer(dataStorage)
            translationZaxis = None

            if geomSingleType:

                boundaryPts = get_boundary_pts(geom)
                height = validate_height(height, boundaryPts)
                try:
                    translationZaxis = get_translation_axis(
                        layer, boundaryPts, elevationLayer, dataStorage
                    )
                except ValueError:
                    return None, None

                result, iterations = polygonToSpeckle(
                    geom, feature, layer, height, translationZaxis, dataStorage, xform
                )

                if result is None:
                    return None, None

                apply_units_to_speckle_polygon(result, units)

                if not isinstance(result, List):
                    result = [result]
                element = GisPolygonElement(units=units, geometry=result)

            else:
                result = []
                all_boundary_pts = []
                all_heights = []
                for poly in geom.parts():
                    boundaryPts = get_boundary_pts(poly)
                    all_boundary_pts.append(boundaryPts)
                    height = validate_height(height, boundaryPts)
                    all_heights.append(height)

                try:
                    translationZaxis = get_translation_axis(
                        layer,
                        [item for sublist in all_boundary_pts for item in sublist],
                        elevationLayer,
                        dataStorage,
                    )
                except ValueError:
                    None, None

                for x, poly in enumerate(geom.parts()):
                    boundaryPts = all_boundary_pts[x]
                    height = all_heights[x]

                    polygon, iterations = polygonToSpeckle(
                        poly,
                        feature,
                        layer,
                        height,
                        translationZaxis,
                        dataStorage,
                        xform,
                    )
                    result.append(polygon)

                for r in result:
                    if r is None:
                        continue
                    apply_units_to_speckle_polygon(r, units)

                element = GisPolygonElement(units=units, geometry=result)

            return element, iterations
        else:
            logToUser(
                "Unsupported or invalid geometry", level=1, func=inspect.stack()[0][3]
            )
        return None, None
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None


def apply_units_to_speckle_polygon(result, units):
    result.units = units
    if result.boundary is not None:
        result.boundary.units = units
    for v in result.voids:
        if v is not None:
            v.units = units
    try:  # if mesh creation failed, displayValue stays None
        for v in result.displayValue:
            if v is not None:
                v.units = units
    except:
        pass


def get_translation_axis(layer, boundaryPts, elevationLayer, dataStorage):
    translationZaxis = None
    if (
        # elevationLayer is not None
        isAppliedLayerTransformByKeywords(
            layer,
            ["polygon", "project", "elevation"],
            [],
            dataStorage,
        )
        is True
    ):
        translationZaxis = getZaxisTranslation(layer, boundaryPts, dataStorage)
        if translationZaxis is None:
            logToUser(
                "Some polygons are outside the elevation layer extent or extrusion value is Null",
                level=1,
                func=inspect.stack()[0][3],
            )
            raise ValueError(
                "Some polygons are outside the elevation layer extent or extrusion value is Null"
            )
    return translationZaxis


def validate_height(height, boundaryPts):
    if height is not None:
        if isFlat(boundaryPts) is False:
            logToUser(
                "Extrusion can only be applied to flat polygons",
                level=1,
                func=inspect.stack()[0][3],
            )
            height = None
    return height


def get_boundary_pts(geom) -> List["QgsPoint"]:
    try:
        boundaryPts = [v[1] for v in enumerate(geom.exteriorRing().vertices())]
    except:
        boundaryPts = [v[1] for v in enumerate(geom.exteriorRing().vertices())]
    return boundaryPts


def convertToNative(base: Base, dataStorage) -> Union["QgsGeometry", None]:
    """Converts any given base object to QgsGeometry."""
    try:
        # print("convertToNative")
        converted = None
        conversions = [
            (Point, pointToNative),
            (Line, lineToNative),
            (Polyline, polylineToNative),
            (Curve, curveToNative),
            (Arc, arcToNative),
            (Ellipse, ellipseToNative),
            (Circle, circleToNative),
            (Mesh, meshToNative),
            (Polycurve, polycurveToNative),
            (GisPolygonGeometry, polygonToNative),
            (
                Base,
                polygonToNative,
            ),  # temporary solution for polygons (Speckle has no type Polygon yet)
        ]

        for conversion in conversions:
            # distinguish normal QGIS polygons and the ones sent as Mesh only
            try:
                # detect hatch

                if isinstance(base, GisPolygonGeometry):
                    if base.boundary is None:
                        try:
                            converted: QgsMultiPolygon = meshToNative(
                                base.displayValue, dataStorage
                            )
                        except:
                            converted: QgsMultiPolygon = meshToNative(
                                base["@displayValue"], dataStorage
                            )
                        break
                    elif isinstance(base, conversion[0]):
                        converted = conversion[1](base, dataStorage)
                        break
                else:
                    # for older commits
                    boundary = base.boundary  # will throw exception if not polygon
                    if boundary is None:
                        try:
                            converted: QgsMultiPolygon = meshToNative(
                                base.displayValue, dataStorage
                            )
                        except:
                            converted: QgsMultiPolygon = meshToNative(
                                base["@displayValue"], dataStorage
                            )
                        break
                    elif boundary is not None and isinstance(base, conversion[0]):
                        converted = conversion[1](base, dataStorage)
                        break

            except:  # if no "boundary" found (either old Mesh from QGIS or other object)
                try:  # check for a QGIS Mesh
                    try:
                        # if sent as Mesh
                        colors = base.displayValue[0].colors  # will throw exception
                        if isinstance(base.displayValue[0], Mesh):
                            converted: QgsMultiPolygon = meshToNative(
                                base.displayValue, dataStorage
                            )  # only called for Meshes created in QGIS before
                    except:
                        # if sent as Mesh
                        colors = base["@displayValue"][0].colors  # will throw exception
                        if isinstance(base["@displayValue"][0], Mesh):
                            converted: QgsMultiPolygon = meshToNative(
                                base["@displayValue"], dataStorage
                            )  # only called for Meshes created in QGIS before

                except:  # any other object
                    if isinstance(base, conversion[0]):
                        converted = conversion[1](base, dataStorage)
                        break

        return converted
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def multiPointToNative(items: List[Point], dataStorage) -> "QgsMultiPoint":
    try:
        pts = QgsMultiPoint()
        for item in items:
            g = pointToNative(item, dataStorage)
            if g is not None:
                pts.addGeometry(g)
        return pts
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def multiPolylineToNative(items: List[Polyline], dataStorage) -> "QgsMultiLineString":
    try:
        polys = QgsMultiLineString()
        for item in items:
            g = polylineToNative(item, dataStorage)
            if g is not None:
                polys.addGeometry(g)
        return polys
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def multiPolygonToNative(items: List[Base], dataStorage) -> "QgsMultiPolygon":
    try:
        polygons = QgsMultiPolygon()
        for item in items:
            g = polygonToNative(item, dataStorage)
            if g is not None:
                polygons.addGeometry(g)
        return polygons
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def convertToNativeMulti(
    items: List[Base], dataStorage
) -> Union["QgsMultiPoint", "QgsMultiLineString", "QgsMultiPolygon", None]:
    try:
        first = items[0]
        if isinstance(first, Point):
            return multiPointToNative(items, dataStorage)
        elif isinstance(first, Line) or isinstance(first, Polyline):
            return multiPolylineToNative(items, dataStorage)
        # elif isinstance(first, Arc) or isinstance(first, Polycurve) or isinstance(first, Ellipse) or isinstance(first, Circle) or isinstance(first, Curve):
        #    return [convertToNative(it, dataStorage) for it in items]
        elif isinstance(first, Mesh):
            converted: QgsMultiPolygon = meshToNative(items, dataStorage)
            return converted
        elif isinstance(first, Base):
            try:
                displayVals = []
                for it in items:
                    try:
                        displayVals.extend(it.displayValue)
                    except:
                        displayVals.extend(it["@displayValue"])
                if isinstance(first, GisPolygonGeometry) or isinstance(first, Mesh):
                    if first.boundary is None:
                        converted: QgsMultiPolygon = meshToNative(
                            displayVals, dataStorage
                        )
                        return converted
                    elif first["boundary"] is not None and first["voids"] is not None:
                        return multiPolygonToNative(items, dataStorage)
                else:
                    # for older commits
                    boundary = first.boundary  # will throw exception if not polygon
                    if boundary is None:
                        converted: QgsMultiPolygon = meshToNative(
                            displayVals, dataStorage
                        )
                        return converted
                    elif boundary is not None:
                        return multiPolygonToNative(items, dataStorage)

            except:  # if no "boundary" found (either old Mesh from QGIS or other object)
                try:
                    if first["boundary"] is not None and first["voids"] is not None:
                        return multiPolygonToNative(items, dataStorage)
                except:
                    return None
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None
