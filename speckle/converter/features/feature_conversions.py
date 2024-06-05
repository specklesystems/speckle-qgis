from datetime import datetime
import inspect
import math
import os
from typing import List, Union

import numpy as np
import hashlib

import scipy as sp
from plugin_utils.helpers import findOrCreatePath, get_scale_factor_to_meter
from speckle.converter.features.GisFeature import GisFeature
from speckle.converter.geometry import transform
from speckle.converter.geometry.conversions import (
    convertToNative,
    convertToNativeMulti,
    convertToSpeckle,
)
from speckle.converter.geometry.mesh import constructMeshFromRaster
from speckle.converter.geometry.utils import apply_pt_offsets_rotation_on_send
from speckle.converter.layers.utils import (
    generate_qgis_app_id,
    get_raster_stats,
    getArrayIndicesFromXY,
    getElevationLayer,
    getHeightWithRemainderFromArray,
    getRasterArrays,
    getVariantFromValue,
    getXYofArrayPoint,
    isAppliedLayerTransformByKeywords,
    validateAttributeName,
)
from speckle.utils.panel_logging import logToUser
from speckle.converter.features.utils import updateFeat
from specklepy.objects.GIS.geometry import (
    GisRasterElement,
    GisPolygonGeometry,
    GisNonGeometryElement,
    GisTopography,
)

from specklepy.objects import Base

try:
    from qgis._core import (
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
    from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
        gdal,
        osr,
    )
    from PyQt5.QtCore import QVariant, QDate, QDateTime
except ModuleNotFoundError:
    pass


def featureToSpeckle(
    fieldnames: List[str],
    f: "QgsFeature",
    geomType,
    selectedLayer: Union["QgsVectorLayer", "QgsRasterLayer"],
    dataStorage,
):
    if dataStorage is None:
        return
    units = dataStorage.currentUnits
    new_report = {"obj_type": "", "errors": ""}
    iterations = 0
    try:
        geom = None
        new_geom = None

        if geomType == "None":
            geom = GisNonGeometryElement()  # redundant, delete in refactor
            new_geom = GisFeature()
            new_report = {"obj_type": geom.speckle_type, "errors": ""}
        else:
            # Try to extract geometry
            skipped_msg = f"'{geomType}' feature skipped due to invalid geometry"
            try:
                geom, iterations = convertToSpeckle(f, selectedLayer, dataStorage)

                if geom is not None and geom != "None":
                    if not isinstance(geom.geometry, List):
                        logToUser(
                            "Geometry not in list format",
                            level=2,
                            func=inspect.stack()[0][3],
                        )
                        return None

                    # geom is GisPointElement, GisLineElement, GisPolygonElement
                    new_geom = GisFeature()
                    new_geom.geometry = []
                    for g in geom.geometry:
                        obj = g
                        if isinstance(g, GisPolygonGeometry):
                            new_geom.displayValue = []
                            obj = GisPolygonGeometry(boundary=g.boundary, voids=g.voids)
                        new_geom.geometry.append(obj)

                    all_errors = ""
                    for g in geom.geometry:
                        if g is None or g == "None":
                            all_errors += skipped_msg + ", "
                            logToUser(skipped_msg, level=2, func=inspect.stack()[0][3])
                        elif isinstance(g, GisPolygonGeometry):
                            if len(g.displayValue) == 0:
                                all_errors += (
                                    "Polygon converted, but display mesh not generated"
                                    + ", "
                                )
                                logToUser(
                                    "Polygon converted, but display mesh not generated",
                                    level=1,
                                    func=inspect.stack()[0][3],
                                )
                            elif iterations is not None and iterations > 0:
                                new_geom.displayValue.extend(g.displayValue)
                                all_errors += (
                                    "Polygon display mesh is simplified" + ", "
                                )
                                logToUser(
                                    "Polygon display mesh is simplified",
                                    level=1,
                                    func=inspect.stack()[0][3],
                                )
                            else:
                                new_geom.displayValue.extend(g.displayValue)

                    if len(geom.geometry) == 0:
                        all_errors = "No geometry converted"
                    new_report.update(
                        {"obj_type": geom.speckle_type, "errors": all_errors}
                    )

                else:  # geom is None, should not happen, but we should pass the object with attributes anyway
                    new_report = {"obj_type": "", "errors": skipped_msg}
                    logToUser(skipped_msg, level=2, func=inspect.stack()[0][3])
                    geom = GisNonGeometryElement()
            except Exception as error:
                new_report = {
                    "obj_type": "",
                    "errors": "Error converting geometry: " + str(error),
                }
                logToUser(
                    "Error converting geometry: " + str(error),
                    level=2,
                    func=inspect.stack()[0][3],
                )

        attributes = Base()
        for name in fieldnames:
            corrected = validateAttributeName(name, fieldnames)
            f_val = f[name]
            if f_val == "NULL" or f_val is None or str(f_val) == "NULL":
                f_val = None
            if isinstance(f[name], list):
                x = ""
                for i, attr in enumerate(f[name]):
                    if i == 0:
                        x += str(attr)
                    else:
                        x += ", " + str(attr)
                f_val = x
            attributes[corrected] = f_val

        # if geom is not None and geom!="None":
        geom.attributes = attributes
        new_geom.attributes = attributes

        dataStorage.latestActionFeaturesReport[
            len(dataStorage.latestActionFeaturesReport) - 1
        ].update(new_report)
        return new_geom

    except Exception as e:
        new_report.update({"errors": e})
        dataStorage.latestActionFeaturesReport[
            len(dataStorage.latestActionFeaturesReport) - 1
        ].update(new_report)
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return new_geom


def rasterFeatureToSpeckle(
    selectedLayer: "QgsRasterLayer",
    projectCRS: "QgsCoordinateReferenceSystem",
    project: "QgsProject",
    plugin,
) -> Base:
    dataStorage = plugin.dataStorage
    if dataStorage is None:
        return

    b = GisRasterElement(units=dataStorage.currentUnits)
    try:
        terrain_transform = False
        texture_transform = False
        # height_list = rasterBandVals[0]
        terrain_transform = isAppliedLayerTransformByKeywords(
            selectedLayer, ["elevation", "mesh"], ["texture"], dataStorage
        )
        texture_transform = isAppliedLayerTransformByKeywords(
            selectedLayer, ["texture"], [], dataStorage
        )
        if terrain_transform is True or texture_transform is True:
            b = GisTopography(units=dataStorage.currentUnits)

        rasterBandCount = selectedLayer.bandCount()
        rasterBandNames = []
        rasterDimensions = [selectedLayer.width(), selectedLayer.height()]
        # if rasterDimensions[0]*rasterDimensions[1] > 1000000 :
        #   logToUser("Large layer: ", level = 1, func = inspect.stack()[0][3])

        ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
        if ds is None:
            return None

        originX = ds.GetGeoTransform()[0]
        originY = ds.GetGeoTransform()[3]
        rasterOriginPoint = QgsPointXY(originX, originY)
        rasterResXY = [float(ds.GetGeoTransform()[1]), float(ds.GetGeoTransform()[5])]
        rasterWkt = ds.GetProjection()
        rasterProj = (
            QgsCoordinateReferenceSystem.fromWkt(rasterWkt)
            .toProj()
            .replace(" +type=crs", "")
        )
        rasterBandNoDataVal = []
        rasterBandMinVal = []
        rasterBandMaxVal = []
        rasterBandVals = []

        # Try to extract geometry
        reprojectedPt = QgsGeometry.fromPointXY(QgsPointXY())
        try:
            reprojectedPt = rasterOriginPoint
            if selectedLayer.crs() != projectCRS:
                reprojectedPt = transform.transform(
                    project, rasterOriginPoint, selectedLayer.crs(), projectCRS
                )
        except Exception as error:
            # logToUser("Error converting point geometry: " + str(error), level = 2, func = inspect.stack()[0][3])
            logToUser("Error converting point geometry: " + str(error), level=2)

        for index in range(rasterBandCount):
            rasterBandNames.append(selectedLayer.bandName(index + 1))
            rb = ds.GetRasterBand(index + 1)
            valMin = (
                selectedLayer.dataProvider()
                .bandStatistics(index + 1, QgsRasterBandStats.All)
                .minimumValue
            )
            valMax = (
                selectedLayer.dataProvider()
                .bandStatistics(index + 1, QgsRasterBandStats.All)
                .maximumValue
            )
            bandVals = rb.ReadAsArray().tolist()

            bandValsFlat = []
            [bandValsFlat.extend(item) for item in bandVals]
            # look at mesh chunking

            const = float(-1 * math.pow(10, 30))
            defaultNoData = rb.GetNoDataValue()
            # print(type(rb.GetNoDataValue()))

            # check whether NA value is too small or raster has too small values
            # assign min value of an actual list; re-assign NA val; replace list items to new NA val
            try:
                # create "safe" fake NA value; replace extreme values with it
                fakeNA = max(bandValsFlat) + 1
                bandValsFlatFake = [
                    fakeNA if val <= const else val for val in bandValsFlat
                ]  # replace all values corresponding to NoData value

                # if default NA value is too small
                if (
                    isinstance(defaultNoData, float) or isinstance(defaultNoData, int)
                ) and defaultNoData < const:
                    # find and rewrite min of actual band values; create new NA value
                    valMin = min(bandValsFlatFake)
                    noDataValNew = valMin - 1000  # use new adequate value
                    rasterBandNoDataVal.append(noDataValNew)
                    # replace fake NA with new NA
                    bandValsFlat = [
                        noDataValNew if val == fakeNA else val
                        for val in bandValsFlatFake
                    ]  # replace all values corresponding to NoData value

                # if default val unaccessible and minimum val is too small
                elif (
                    isinstance(defaultNoData, str) or defaultNoData is None
                ) and valMin < const:  # if there are extremely small values but default NA unaccessible
                    noDataValNew = valMin
                    rasterBandNoDataVal.append(noDataValNew)
                    # replace fake NA with new NA
                    bandValsFlat = [
                        noDataValNew if val == fakeNA else val
                        for val in bandValsFlatFake
                    ]  # replace all values corresponding to NoData value
                    # last, change minValto actual one
                    valMin = min(bandValsFlatFake)

                else:
                    rasterBandNoDataVal.append(rb.GetNoDataValue())

            except:
                rasterBandNoDataVal.append(rb.GetNoDataValue())

            rasterBandVals.append(bandValsFlat)
            rasterBandMinVal.append(valMin)
            rasterBandMaxVal.append(valMax)
            b["@(10000)" + selectedLayer.bandName(index + 1) + "_values"] = (
                bandValsFlat  # [0:int(max_values/rasterBandCount)]
            )

        b.x_resolution = rasterResXY[0]
        b.y_resolution = rasterResXY[1]
        b.x_size = rasterDimensions[0]
        b.y_size = rasterDimensions[1]
        b.x_origin, b.y_origin = apply_pt_offsets_rotation_on_send(
            reprojectedPt.x(), reprojectedPt.y(), dataStorage
        )
        b.band_count = rasterBandCount
        b.band_names = rasterBandNames
        b.noDataValue = rasterBandNoDataVal
        # creating a mesh
        count = 0
        rendererType = selectedLayer.renderer().type()

        xy_list = []
        z_list = []
        # print(rendererType)
        # identify symbology type and if Multiband, which band is which color

        #############################################################

        elevationLayer = None
        elevationProj = None
        if texture_transform is True:
            elevationLayer = getElevationLayer(dataStorage)
        elif terrain_transform is True:
            elevationLayer = selectedLayer

        if elevationLayer is not None:
            settings_elevation_layer = get_raster_stats(elevationLayer)
            (
                elevationResX,
                elevationResY,
                elevationOriginX,
                elevationOriginY,
                elevationSizeX,
                elevationSizeY,
                elevationWkt,
                elevationProj,
            ) = settings_elevation_layer

            # reproject the elevation layer
            if (
                elevationProj is not None
                and rasterProj is not None
                and elevationProj != rasterProj
            ):
                try:
                    p = (
                        os.path.expandvars(r"%LOCALAPPDATA%")
                        + "\\Temp\\Speckle_QGIS_temp\\"
                        + datetime.now().strftime("%Y-%m-%d_%H-%M")
                    )
                    findOrCreatePath(p)
                    path = p
                    out = p + "\\out.tif"
                    gdal.Warp(
                        out,
                        elevationLayer.source(),
                        dstSRS=selectedLayer.crs().authid(),
                        xRes=elevationResX,
                        yRes=elevationResY,
                    )

                    elevationLayer = QgsRasterLayer(out, "", "gdal")
                    settings_elevation_layer = get_raster_stats(elevationLayer)
                    (
                        elevationResX,
                        elevationResY,
                        elevationOriginX,
                        elevationOriginY,
                        elevationSizeX,
                        elevationSizeY,
                        elevationWkt,
                        elevationProj,
                    ) = settings_elevation_layer
                except Exception as e:
                    logToUser(f"Reprojection did not succeed: {e}", level=0)
            elevation_arrays, all_mins, all_maxs, all_na = getRasterArrays(
                elevationLayer
            )
            array_band = elevation_arrays[0]

            height_array = np.where(
                (array_band < const)
                | (array_band > -1 * const)
                | (array_band == all_na[0]),
                np.nan,
                array_band,
            )
            try:
                height_array = height_array.astype(float)
            except:
                try:
                    arr = []
                    for row in height_array:
                        new_row = []
                        for item in row:
                            try:
                                new_row.append(float(item))
                            except:
                                new_row.append(np.nan)
                        arr.append(new_row)
                    height_array = np.array(arr).astype(float)
                except:
                    height_array = height_array[
                        [isinstance(i, float) for i in height_array]
                    ]
        else:
            elevation_arrays = all_mins = all_maxs = all_na = None
            elevationResX = elevationResY = elevationOriginX = elevationOriginY = (
                elevationSizeX
            ) = elevationSizeY = elevationWkt = None
            height_array = None

        largeTransform = False
        if texture_transform is True and elevationLayer is None:
            logToUser(
                f"Elevation layer is not found. Texture transformation for layer '{selectedLayer.name()}' will not be applied",
                level=1,
                plugin=plugin.dockwidget,
            )
        elif (
            texture_transform is True
            and rasterDimensions[1] * rasterDimensions[0] >= 10000
            and elevationProj is not None
            and rasterProj is not None
            and elevationProj != rasterProj
        ):
            # warning if >= 100x100 raster is being projected to an elevation with different CRS
            logToUser(
                f"Texture transformation for the layer '{selectedLayer.name()}' might take a while 🕒\nTip: reproject one of the layers (texture or elevation) to the other layer's CRS. When both layers have the same CRS, texture transformation will be much faster.",
                level=0,
                plugin=plugin.dockwidget,
            )
            largeTransform = True
        elif (
            texture_transform is True
            and rasterDimensions[1] * rasterDimensions[0] >= 250000
        ):
            # warning if >= 500x500 raster is being projected to any elevation
            logToUser(
                f"Texture transformation for the layer '{selectedLayer.name()}' might take a while 🕒",
                level=0,
                plugin=plugin.dockwidget,
            )
            largeTransform = True
        ############################################################
        faces_array = []
        colors_array = []
        vertices_array = []
        array_z = []  # size is large by 1 than the raster size, in both dimensions
        time0 = datetime.now()
        for v in range(rasterDimensions[1]):  # each row, Y
            if largeTransform is True:
                if v == int(rasterDimensions[1] / 20):
                    logToUser(
                        f"Converting layer '{selectedLayer.name()}': 5%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] / 10):
                    logToUser(
                        f"Converting layer '{selectedLayer.name()}': 10%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name()}': 20%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 2 / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name()}': 40%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 3 / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name()}': 60%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 4 / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name()}': 80%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 9 / 10):
                    logToUser(
                        f"Converting layer '{selectedLayer.name()}': 90%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
            vertices = []
            faces = []
            colors = []
            row_z = []
            row_z_bottom = []
            for h in range(rasterDimensions[0]):  # item in a row, X
                pt1 = QgsPointXY(
                    rasterOriginPoint.x() + h * rasterResXY[0],
                    rasterOriginPoint.y() + v * rasterResXY[1],
                )
                pt2 = QgsPointXY(
                    rasterOriginPoint.x() + h * rasterResXY[0],
                    rasterOriginPoint.y() + (v + 1) * rasterResXY[1],
                )
                pt3 = QgsPointXY(
                    rasterOriginPoint.x() + (h + 1) * rasterResXY[0],
                    rasterOriginPoint.y() + (v + 1) * rasterResXY[1],
                )
                pt4 = QgsPointXY(
                    rasterOriginPoint.x() + (h + 1) * rasterResXY[0],
                    rasterOriginPoint.y() + v * rasterResXY[1],
                )
                # first, get point coordinates with correct position and resolution, then reproject each:
                if selectedLayer.crs() != projectCRS:
                    pt1 = transform.transform(
                        project, src=pt1, crsSrc=selectedLayer.crs(), crsDest=projectCRS
                    )
                    pt2 = transform.transform(
                        project, src=pt2, crsSrc=selectedLayer.crs(), crsDest=projectCRS
                    )
                    pt3 = transform.transform(
                        project, src=pt3, crsSrc=selectedLayer.crs(), crsDest=projectCRS
                    )
                    pt4 = transform.transform(
                        project, src=pt4, crsSrc=selectedLayer.crs(), crsDest=projectCRS
                    )

                z1 = z2 = z3 = z4 = 0
                index1 = index1_0 = None

                #############################################################
                if (
                    terrain_transform is True or texture_transform is True
                ) and height_array is not None:
                    if texture_transform is True:  # texture
                        # index1: index on y-scale
                        posX, posY = getXYofArrayPoint(
                            (
                                rasterResXY[0],
                                rasterResXY[1],
                                originX,
                                originY,
                            ),
                            h,
                            v,
                            selectedLayer,
                            elevationLayer,
                            dataStorage,
                        )

                        index1, index2, remainder1, remainder2 = getArrayIndicesFromXY(
                            (
                                elevationResX,
                                elevationResY,
                                elevationOriginX,
                                elevationOriginY,
                                elevationSizeX,
                                elevationSizeY,
                                elevationWkt,
                                elevationProj,
                            ),
                            posX,
                            posY,
                        )
                        (
                            index1_0,
                            index2_0,
                            remainder1_0,
                            remainder2_0,
                        ) = getArrayIndicesFromXY(
                            (
                                elevationResX,
                                elevationResY,
                                elevationOriginX,
                                elevationOriginY,
                                elevationSizeX,
                                elevationSizeY,
                                elevationWkt,
                                elevationProj,
                            ),
                            posX - rasterResXY[0],
                            posY - rasterResXY[1],
                        )
                    else:  # elevation
                        index1 = v
                        index1_0 = v - 1
                        index2 = h
                        index2_0 = h - 1

                    if index1 is None or index1_0 is None:
                        # count += 4
                        # continue # skip the pixel
                        z1 = z2 = z3 = z4 = np.nan
                    else:
                        # top vertices ######################################
                        try:
                            z1 = z_list[xy_list.index((pt1.x(), pt1.y()))]
                        except:
                            if index1 > 0 and index2 > 0:
                                z1 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1_0, index2_0
                                )
                            elif index1 > 0:
                                z1 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1_0, index2
                                )
                            elif index2 > 0:
                                z1 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1, index2_0
                                )
                            else:
                                z1 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1, index2
                                )

                            if z1 is not None:
                                z_list.append(z1)
                                xy_list.append((pt1.x(), pt1.y()))

                        #################### z4
                        try:
                            z4 = z_list[xy_list.index((pt4.x(), pt4.y()))]
                        except:
                            if index1 > 0:
                                z4 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1_0, index2
                                )
                            else:
                                z4 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1, index2
                                )

                            if z4 is not None:
                                z_list.append(z4)
                                xy_list.append((pt4.x(), pt4.y()))

                        # bottom vertices ######################################
                        z3 = getHeightWithRemainderFromArray(
                            height_array, texture_transform, index1, index2
                        )
                        if z3 is not None:
                            z_list.append(z3)
                            xy_list.append((pt3.x(), pt3.y()))

                        try:
                            z2 = z_list[xy_list.index((pt2.x(), pt2.y()))]
                        except:
                            if index2 > 0:
                                z2 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1, index2_0
                                )
                            else:
                                z2 = getHeightWithRemainderFromArray(
                                    height_array, texture_transform, index1, index2
                                )
                            if z2 is not None:
                                z_list.append(z2)
                                xy_list.append((pt2.x(), pt2.y()))

                        ##############################################

                    max_len = rasterDimensions[0] * 4 + 4
                    if len(z_list) > max_len:
                        z_list = z_list[len(z_list) - max_len :]
                        xy_list = xy_list[len(xy_list) - max_len :]

                    ### list to smoothen later:
                    if h == 0:
                        row_z.append(z1)
                        row_z_bottom.append(z2)
                    row_z.append(z4)
                    row_z_bottom.append(z3)

                ########################################################
                x1, y1 = apply_pt_offsets_rotation_on_send(
                    pt1.x(), pt1.y(), dataStorage
                )
                x2, y2 = apply_pt_offsets_rotation_on_send(
                    pt2.x(), pt2.y(), dataStorage
                )
                x3, y3 = apply_pt_offsets_rotation_on_send(
                    pt3.x(), pt3.y(), dataStorage
                )
                x4, y4 = apply_pt_offsets_rotation_on_send(
                    pt4.x(), pt4.y(), dataStorage
                )

                vertices.append(
                    [x1, y1, z1, x2, y2, z2, x3, y3, z3, x4, y4, z4]
                )  ## add 4 points
                current_vertices = (
                    v * rasterDimensions[0] * 4 + h * 4
                )  # len(np.array(faces_array).flatten()) * 4 / 5
                faces.append(
                    [
                        4,
                        current_vertices,
                        current_vertices + 1,
                        current_vertices + 2,
                        current_vertices + 3,
                    ]
                )

                # color vertices according to QGIS renderer
                alpha = 255
                color = (alpha << 24) + (0 << 16) + (0 << 8) + 0
                noValColor: tuple[int] = (
                    selectedLayer.renderer().nodataColor().getRgb()
                )  # RGB or RGBA, 3 or 4 values

                colorLayer = selectedLayer
                currentRasterBandCount = rasterBandCount

                if (
                    (terrain_transform is True or texture_transform is True)
                    and height_array is not None
                    and (index1 is None or index1_0 is None)
                ):  # transparent color
                    alpha = 0
                    color = (alpha << 24) + (0 << 16) + (0 << 8) + 0
                elif rendererType == "multibandcolor":
                    valR = 0
                    valG = 0
                    valB = 0
                    bandRed = int(colorLayer.renderer().redBand())
                    bandGreen = int(colorLayer.renderer().greenBand())
                    bandBlue = int(colorLayer.renderer().blueBand())

                    for k in range(currentRasterBandCount):
                        valRange = rasterBandMaxVal[k] - rasterBandMinVal[k]
                        if valRange == 0:
                            colorVal = 0
                        elif (
                            rasterBandVals[k][int(count / 4)] == rasterBandNoDataVal[k]
                        ):
                            colorVal = 0
                            alpha = 0
                        #   break
                        else:
                            colorVal = int(
                                (
                                    rasterBandVals[k][int(count / 4)]
                                    - rasterBandMinVal[k]
                                )
                                / valRange
                                * 255
                            )

                        if k + 1 == bandRed:
                            valR = colorVal
                        if k + 1 == bandGreen:
                            valG = colorVal
                        if k + 1 == bandBlue:
                            valB = colorVal

                    color = (alpha << 24) + (valR << 16) + (valG << 8) + valB

                elif rendererType == "paletted":
                    bandIndex = colorLayer.renderer().band() - 1  # int
                    # if textureLayer is not None:
                    #    value = texture_arrays[bandIndex][index1][index2]
                    # else:
                    value = rasterBandVals[bandIndex][
                        int(count / 4)
                    ]  # find in the list and match with color

                    rendererClasses = colorLayer.renderer().classes()
                    for c in range(len(rendererClasses) - 1):
                        if (
                            value >= rendererClasses[c].value
                            and value <= rendererClasses[c + 1].value
                        ):
                            rgb = rendererClasses[c].color.getRgb()
                            color = (
                                (255 << 24) + (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]
                            )
                            break
                    if value == rasterBandNoDataVal[bandIndex]:
                        alpha = 0
                        color = (alpha << 24) + (0 << 16) + (0 << 8) + 0

                elif rendererType == "singlebandpseudocolor":
                    bandIndex = colorLayer.renderer().band() - 1  # int
                    # if textureLayer is not None:
                    #    value = texture_arrays[bandIndex][index1][index2]
                    # else:
                    value = rasterBandVals[bandIndex][
                        int(count / 4)
                    ]  # find in the list and match with color

                    rendererClasses = colorLayer.renderer().legendSymbologyItems()
                    for c in range(len(rendererClasses) - 1):
                        if value >= float(rendererClasses[c][0]) and value <= float(
                            rendererClasses[c + 1][0]
                        ):
                            rgb = rendererClasses[c][1].getRgb()
                            color = (
                                (255 << 24) + (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]
                            )
                            break
                    if value == rasterBandNoDataVal[bandIndex]:
                        alpha = 0
                        color = (alpha << 24) + (0 << 16) + (0 << 8) + 0

                else:
                    if rendererType == "singlebandgray":
                        bandIndex = colorLayer.renderer().grayBand() - 1
                    elif rendererType == "hillshade":
                        bandIndex = colorLayer.renderer().band() - 1
                    elif rendererType == "contour":
                        try:
                            bandIndex = colorLayer.renderer().inputBand() - 1
                        except:
                            try:
                                bandIndex = colorLayer.renderer().band() - 1
                            except:
                                bandIndex = 0
                    else:  # e.g. single band data
                        bandIndex = 0

                    value = rasterBandVals[bandIndex][int(count / 4)]
                    if (
                        rasterBandMinVal[bandIndex]
                        <= value
                        <= rasterBandMaxVal[bandIndex]
                    ):
                        # REMAP band values to (0,255) range
                        valRange = (
                            rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex]
                        )
                        if valRange == 0:
                            colorVal = 0
                        else:
                            colorVal = int(
                                (
                                    rasterBandVals[bandIndex][int(count / 4)]
                                    - rasterBandMinVal[bandIndex]
                                )
                                / valRange
                                * 255
                            )
                        color = (
                            (alpha << 24)
                            + (colorVal << 16)
                            + (colorVal << 8)
                            + colorVal
                        )
                    elif value == rasterBandNoDataVal[bandIndex]:
                        alpha = 0
                        color = (alpha << 24) + (0 << 16) + (0 << 8) + 0

                colors.append([color, color, color, color])
                count += 4

            # after each row
            vertices_array.append(vertices)
            faces_array.append(faces)
            colors_array.append(colors)

            if v == 0:
                array_z.append(row_z)
            array_z.append(row_z_bottom)

        time1 = datetime.now()
        # print(f"Time to get Raster: {(time1-time0).total_seconds()} sec")
        # after the entire loop
        faces_filtered = []
        colors_filtered = []
        vertices_filtered = []

        ## end of the the table
        smooth = False
        if terrain_transform is True or texture_transform is True:
            smooth = True
        if smooth is True and len(row_z) > 2 and len(array_z) > 2:
            array_z_nans = np.array(array_z)

            array_z_filled = np.array(array_z)
            mask = np.isnan(array_z_filled)
            array_z_filled[mask] = np.interp(
                np.flatnonzero(mask), np.flatnonzero(~mask), array_z_filled[~mask]
            )

            sigma = 0.8  # for elevation
            if texture_transform is True:
                sigma = 1  # for texture

                # increase sigma if needed
                try:
                    unitsRaster = QgsUnitTypes.encodeUnit(
                        selectedLayer.crs().mapUnits()
                    )
                    unitsElevation = QgsUnitTypes.encodeUnit(
                        elevationLayer.crs().mapUnits()
                    )
                    # print(unitsRaster)
                    # print(unitsElevation)
                    resRasterX = get_scale_factor_to_meter(unitsRaster) * rasterResXY[0]
                    resElevX = get_scale_factor_to_meter(unitsElevation) * elevationResX
                    # print(resRasterX)
                    # print(resElevX)
                    if resRasterX / resElevX >= 2 or resElevX / resRasterX >= 2:
                        sigma = math.sqrt(
                            max(resRasterX / resElevX, resElevX / resRasterX)
                        )
                        # print(sigma)
                except:
                    pass

            gaussian_array = sp.ndimage.filters.gaussian_filter(
                array_z_filled, sigma, mode="nearest"
            )

            for v in range(rasterDimensions[1]):  # each row, Y
                for h in range(rasterDimensions[0]):  # item in a row, X
                    if not np.isnan(array_z_nans[v][h]):
                        vertices_item = vertices_array[v][h]
                        # print(vertices_item)
                        vertices_item[2] = gaussian_array[v][h]
                        vertices_item[5] = gaussian_array[v + 1][h]
                        vertices_item[8] = gaussian_array[v + 1][h + 1]
                        vertices_item[11] = gaussian_array[v][h + 1]
                        vertices_filtered.extend(vertices_item)

                        currentFaces = len(faces_filtered) / 5 * 4
                        faces_filtered.extend(
                            [
                                4,
                                currentFaces,
                                currentFaces + 1,
                                currentFaces + 2,
                                currentFaces + 3,
                            ]
                        )
                        # print(faces_filtered)
                        colors_filtered.extend(colors_array[v][h])
                        # print(colors_array[v][h])
        else:
            faces_filtered = np.array(faces_array).flatten().tolist()
            colors_filtered = np.array(colors_array).flatten().tolist()
            vertices_filtered = np.array(vertices_array).flatten().tolist()

        # if len(colors)/4*5 == len(faces) and len(colors)*3 == len(vertices):
        mesh = constructMeshFromRaster(
            vertices_filtered, faces_filtered, colors_filtered, dataStorage
        )
        if mesh is not None:
            mesh.units = dataStorage.currentUnits
            b.displayValue = [mesh]
        else:
            logToUser(
                "Something went wrong. Mesh cannot be created, only raster data will be sent. ",
                level=2,
                plugin=plugin.dockwidget,
            )

        return b

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        raise e


def featureToNative(feature: Base, fields: "QgsFields", dataStorage):
    feat = QgsFeature()
    # print("___featureToNative")
    try:
        qgsGeom = None

        if isinstance(feature, GisNonGeometryElement) or (
            isinstance(feature, GisFeature) and feature.geometry is None
        ):
            pass
        else:
            try:
                speckle_geom = (
                    feature.geometry
                )  # for QGIS / ArcGIS Layer type from 2.14
            except:
                try:
                    speckle_geom = feature[
                        "geometry"
                    ]  # for QGIS / ArcGIS Layer type before 2.14
                except:
                    speckle_geom = feature  # for created in other software

            if not isinstance(speckle_geom, list):
                qgsGeom = convertToNative(speckle_geom, dataStorage)

            elif isinstance(speckle_geom, list):
                # add condition for new GisFeature class
                if isinstance(feature, GisFeature) and isinstance(speckle_geom[0], GisPolygonGeometry) and speckle_geom[0].boundary is None:
                    qgsGeom = convertToNativeMulti(feature.displayValue, dataStorage)
                elif len(speckle_geom) == 1:
                    qgsGeom = convertToNative(speckle_geom[0], dataStorage)
                elif len(speckle_geom) > 1:
                    qgsGeom = convertToNativeMulti(speckle_geom, dataStorage)
                else:
                    logToUser(
                        f"Feature '{feature.id}' does not contain geometry",
                        level=2,
                        func=inspect.stack()[0][3],
                    )

            if qgsGeom is not None:
                feat.setGeometry(qgsGeom)
            else:
                return None

        feat.setFields(fields)
        for field in fields:
            name = str(field.name())
            variant = field.type()
            # if name == "id": feat[name] = str(feature["applicationId"])

            try:
                value = feature.attributes[name]  # fro 2.14 onwards
            except:
                try:
                    value = feature[name]
                except:
                    if name == "Speckle_ID":
                        try:
                            value = str(
                                feature["Speckle_ID"]
                            )  # if GIS already generated this field
                        except:
                            try:
                                value = str(feature["speckle_id"])
                            except:
                                value = str(feature["id"])
                    else:
                        value = None
                        # logger.logToUser(f"Field {name} not found", Qgis.Warning)
                        # return None

            if variant == QVariant.String:
                value = str(value)

            if isinstance(value, str) and variant == QVariant.Date:  # 14
                y, m, d = value.split("(")[1].split(")")[0].split(",")[:3]
                value = QDate(int(y), int(m), int(d))
            elif isinstance(value, str) and variant == QVariant.DateTime:
                y, m, d, t1, t2 = value.split("(")[1].split(")")[0].split(",")[:5]
                value = QDateTime(int(y), int(m), int(d), int(t1), int(t2))

            if (
                variant == getVariantFromValue(value)
                and value != "NULL"
                and value != "None"
            ):
                feat[name] = value

        dataStorage.flat_report_receive.update(
            {
                feature.applicationId: {
                    "speckle_id": feature.id,
                    "hash": generate_qgis_app_id(None, feat),
                    "layer_name": dataStorage.latestActionLayers[-1],
                    "attributes": [attr for attr in feat.attributes()],
                    "geometry": str(feat.geometry()),
                }
            }
        )
        return feat
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return feat


def bimFeatureToNative(
    exist_feat: "QgsFeature",
    feature: Base,
    fields: "QgsFields",
    crs,
    path: str,
    dataStorage,
):
    # print("04_________BIM Feature To Native____________")
    try:
        exist_feat.setFields(fields)

        feat_updated = updateFeat(exist_feat, fields, feature)
        # print(fields.toList())
        # print(feature)
        # print(feat_updated)
        dataStorage.flat_report_receive.update(
            {
                feature.applicationId: {
                    "speckle_id": feature.id,
                    "hash": generate_qgis_app_id(None, feat_updated),
                    "layer_name": dataStorage.latestActionLayers[-1],
                    "attributes": [attr for attr in feat_updated.attributes()],
                    "geometry": str(feat_updated.geometry()),
                }
            }
        )
        return feat_updated
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def nonGeomFeatureToNative(feature: Base, fields: "QgsFields", dataStorage):
    try:
        exist_feat = QgsFeature()
        exist_feat.setFields(fields)
        feat_updated = updateFeat(exist_feat, fields, feature)
        dataStorage.flat_report_receive.update(
            {
                feature.applicationId: {
                    "speckle_id": feature.id,
                    "hash": generate_qgis_app_id(None, feat_updated),
                    "layer_name": dataStorage.latestActionLayers[-1],
                    "attributes": [attr for attr in feat_updated.attributes()],
                    "geometry": "",
                }
            }
        )
        return feat_updated

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def cadFeatureToNative(feature: Base, fields: "QgsFields", dataStorage):
    try:
        exist_feat = QgsFeature()
        try:
            speckle_geom = feature["geometry"]  # for created in QGIS Layer type
        except:
            speckle_geom = feature  # for created in other software

        if isinstance(speckle_geom, list):
            qgsGeom = convertToNativeMulti(speckle_geom, dataStorage)
        else:
            qgsGeom = convertToNative(speckle_geom, dataStorage)

        if qgsGeom is not None:
            exist_feat.setGeometry(qgsGeom)
        else:
            return

        exist_feat.setFields(fields)
        feat_updated = updateFeat(exist_feat, fields, feature)
        dataStorage.flat_report_receive.update(
            {
                feature.applicationId: {
                    "speckle_id": feature.id,
                    "hash": generate_qgis_app_id(None, feat_updated),
                    "layer_name": dataStorage.latestActionLayers[-1],
                    "attributes": [attr for attr in feat_updated.attributes()],
                    "geometry": str(feat_updated.geometry()),
                }
            }
        )
        return feat_updated
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return
