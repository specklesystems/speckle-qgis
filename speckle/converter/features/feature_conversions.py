from datetime import datetime
import inspect
import math
import os
from typing import Dict, List, Union

import numpy as np
import hashlib

import scipy as sp
from plugin_utils.helpers import findOrCreatePath
from speckle.converter.features.GisFeature import GisFeature
from speckle.converter.geometry import transform
from speckle.converter.geometry.conversions import (
    convertToNative,
    convertToNativeMulti,
    convertToSpeckle,
)
from speckle.converter.geometry.mesh import constructMeshFromRaster
from speckle.converter.geometry.utils import apply_pt_offsets_rotation_on_send
from speckle.converter.layers.symbology import get_a_r_g_b
from speckle.converter.layers.utils import (
    generate_qgis_app_id,
    getArrayIndicesFromXY,
    getElevationLayer,
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
                                    "Polygon part converted, but display mesh not generated"
                                    + ", "
                                )
                                logToUser(
                                    "Polygon part converted, but display mesh not generated",
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


def show_progress(current_row: int, rows: int, layer_name: str, plugin: "SpeckleQGIS"):
    """Updates UI with raster conversion %."""
    percentage: int = int(current_row / rows)  # i = percentage
    if percentage % 10 == 0 or percentage == 5:
        logToUser(
            f"Converting layer '{layer_name}': {percentage}%...",
            level=0,
            plugin=plugin.dockwidget,
        )


def reproject_raster(layer, crs, resolutionX, resolutionY):
    if layer.crs() == crs:
        return layer
    path = (
        os.path.expandvars(r"%LOCALAPPDATA%")
        + "\\Temp\\Speckle_QGIS_temp\\"
        + datetime.now().strftime("%Y-%m-%d_%H-%M")
    )
    findOrCreatePath(path)

    out = path + "\\out.tif"
    file = gdal.Warp(
        out,
        layer.source(),
        dstSRS=crs.authid(),
        xRes=resolutionX,
        yRes=resolutionY,
    )
    return QgsRasterLayer(out, "", "gdal")


def get_raster_mesh_coords(
    reprojected_raster_stats,
    rasterResXY: list,
    band1_values: list,
    dataStorage,
) -> List[float]:
    (
        reprojected_top_right,
        reprojectedOriginPt,
        reprojectedMaxPt,
        reprojected_bottom_left,
        rasterResXY_reprojected,
        rasterDimensions,
    ) = reprojected_raster_stats

    xOrigin = reprojectedOriginPt.x()
    yOrigin = reprojectedOriginPt.y()
    sizeX = rasterDimensions[0]
    x_correction = (reprojected_bottom_left.x() - xOrigin) / sizeX
    y_correction = (reprojected_top_right.y() - yOrigin) / rasterDimensions[1]

    list_nested = [
        (
            xOrigin
            + rasterResXY[0]
            * (ind % sizeX)  # ind%sizeX = current item index in the row; +1 = next item
            + x_correction * (ind % sizeX),
            yOrigin
            + rasterResXY[1]
            * math.floor(
                ind / sizeX
            )  # math.floor(ind/sizeX) = current row index; +1 = next row
            + y_correction * math.floor(ind / sizeX),
            0,
            xOrigin + rasterResXY[0] * (ind % sizeX) + x_correction * (ind % sizeX),
            yOrigin
            + rasterResXY[1] * math.floor(ind / sizeX + 1)
            + y_correction * math.floor(ind / sizeX + 1),
            0,
            xOrigin
            + rasterResXY[0] * (ind % sizeX + 1)
            + x_correction * (ind % sizeX + 1),
            yOrigin
            + rasterResXY[1] * math.floor(ind / sizeX + 1)
            + y_correction * math.floor(ind / sizeX + 1),
            0,
            xOrigin
            + rasterResXY[0] * (ind % sizeX + 1)
            + x_correction * (ind % sizeX + 1),
            yOrigin
            + rasterResXY[1] * math.floor(ind / sizeX)
            + y_correction * math.floor(ind / sizeX),
            0,
        )
        for ind, _ in enumerate(band1_values)
    ]
    list_flattened = [item for sublist in list_nested for item in sublist]

    return list_flattened


def apply_offset_rotation_to_vertices_send(vertices: List[float], dataStorage):
    new_vertices = []
    for index in range(int(len(vertices) / 3)):
        x, y = apply_pt_offsets_rotation_on_send(
            vertices[3 * index], vertices[3 * index + 1], dataStorage
        )
        new_vertices.extend([x, y, vertices[3 * index + 2]])

    return new_vertices


def get_raster_colors(
    layer,
    rasterBandVals,
    rasterBandNoDataVal,
    rasterBandMinVal,
    rasterBandMaxVal,
    rendererType,
    plugin,
):
    list_colors = []
    have_transparent_cells = False
    if rendererType == "multibandcolor":

        # mock values for R,G,B channels
        vals_red = [0 for _ in rasterBandVals[0]]
        vals_green = [0 for _ in rasterBandVals[0]]
        vals_blue = [0 for _ in rasterBandVals[0]]
        vals_alpha = None

        vals_range_red = 1
        vals_range_green = 1
        vals_range_blue = 1

        val_min_red = 0
        val_min_green = 0
        val_min_blue = 0

        val_na_red = None
        val_na_green = None
        val_na_blue = None

        # get band index for each color channel
        bandRed = int(layer.renderer().redBand())
        bandGreen = int(layer.renderer().greenBand())
        bandBlue = int(layer.renderer().blueBand())
        bandAlpha = int(layer.renderer().alphaBand())

        # assign correct values to R,G,B channels, where available
        for band_index in range(len(rasterBandVals)):
            # if statements are not exclusive, as QGIS allows to assugn 1 band to several color channels
            if band_index + 1 == bandRed:
                vals_red = rasterBandVals[band_index]
                vals_range_red = (
                    rasterBandMaxVal[band_index] - rasterBandMinVal[band_index]
                )
                val_min_red = rasterBandMinVal[band_index]
                val_na_red = rasterBandNoDataVal[band_index]
            if band_index + 1 == bandGreen:
                vals_green = rasterBandVals[band_index]
                vals_range_green = (
                    rasterBandMaxVal[band_index] - rasterBandMinVal[band_index]
                )
                val_min_green = rasterBandMinVal[band_index]
                val_na_green = rasterBandNoDataVal[band_index]
            if band_index + 1 == bandBlue:
                vals_blue = rasterBandVals[band_index]
                vals_range_blue = (
                    rasterBandMaxVal[band_index] - rasterBandMinVal[band_index]
                )
                val_min_blue = rasterBandMinVal[band_index]
                val_na_blue = rasterBandNoDataVal[band_index]
            if band_index + 1 == bandAlpha:
                vals_range_alpha = (
                    rasterBandMaxVal[band_index] - rasterBandMinVal[band_index]
                )
                val_min_alpha = rasterBandMinVal[band_index]
                val_na_alpha = rasterBandNoDataVal[band_index]
                vals_alpha = rasterBandVals[band_index]

        if vals_alpha is not None and 0 in vals_alpha:
            have_transparent_cells = True

        list_colors = [
            (
                (
                    255
                    if vals_alpha is None
                    else int(255 * (vals_alpha[ind] - val_min_alpha) / vals_range_alpha)
                    << 24
                )
                | (int(255 * (vals_red[ind] - val_min_red) / vals_range_red) << 16)
                | (int(255 * (vals_green[ind] - val_min_green) / vals_range_green) << 8)
                | int(255 * (vals_blue[ind] - val_min_blue) / vals_range_blue)
                if (
                    vals_red[ind] != val_na_red
                    and vals_green[ind] != val_na_green
                    and vals_blue[ind] != val_na_blue
                )
                else (0 << 24) + (0 << 16) + (0 << 8) + 0
            )
            for ind, _ in enumerate(rasterBandVals[0])
            for _ in range(4)
        ]

    elif rendererType == "paletted":
        try:
            bandIndex = layer.renderer().band() - 1  # int
            renderer_classes = layer.renderer().classes()
            class_rgbs = [
                renderer_classes[class_ind].color.getRgb()
                for class_ind in range(len(renderer_classes))
            ]

            for val in rasterBandVals[bandIndex]:
                rgb = None
                color = (0 << 24) + (0 << 16) + (0 << 8) + 0

                for class_ind in range(len(renderer_classes)):
                    if rasterBandVals[bandIndex] == rasterBandNoDataVal[bandIndex]:
                        rgb = None
                    elif class_ind < len(renderer_classes) - 1:
                        if val >= float(
                            renderer_classes[class_ind].value
                        ) and val < float(renderer_classes[class_ind + 1].value):
                            rgb = class_rgbs[class_ind]
                    elif class_ind == len(renderer_classes) - 1 and val >= float(
                        renderer_classes[class_ind].value
                    ):
                        rgb = class_rgbs[class_ind]

                if rgb is not None:
                    color = (255 << 24) + (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]

                # add color value after looping through classes/categories
                list_colors.extend([color, color, color, color])

        except Exception as e:
            # log warning, but don't prevent conversion
            logToUser(
                f"Raster renderer of type '{rendererType}' couldn't read the renderer class values, default renderer will be applied: {e}",
                level=1,
                func=inspect.stack()[0][3],
                plugin=plugin.dockwidget,
            )

            return get_raster_colors(
                layer,
                rasterBandVals,
                rasterBandNoDataVal,
                rasterBandMinVal,
                rasterBandMaxVal,
                None,
                plugin,
            )

    elif rendererType == "singlebandpseudocolor":
        try:
            bandIndex = layer.renderer().band() - 1  # int

            renderer_classes = layer.renderer().legendSymbologyItems()
            class_rgbs = [
                renderer_classes[class_ind][1].getRgb()
                for class_ind in range(len(renderer_classes))
            ]

            for val in rasterBandVals[bandIndex]:
                rgb = None
                color = (0 << 24) + (0 << 16) + (0 << 8) + 0

                for class_ind in range(len(renderer_classes)):
                    if rasterBandVals[bandIndex] == rasterBandNoDataVal[bandIndex]:
                        rgb = None
                    elif class_ind < len(renderer_classes) - 1:
                        if val >= float(renderer_classes[class_ind][0]) and val < float(
                            renderer_classes[class_ind + 1][0]
                        ):
                            rgb = class_rgbs[class_ind]
                    elif class_ind == len(renderer_classes) - 1 and val >= float(
                        renderer_classes[class_ind][0]
                    ):
                        rgb = class_rgbs[class_ind]

                if rgb is not None:
                    color = (255 << 24) + (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]

                # add color value after looping through classes/categories
                list_colors.extend([color, color, color, color])

        except Exception as e:
            # log warning, but don't prevent conversion
            logToUser(
                f"Raster renderer of type '{rendererType}' couldn't read the renderer class values, default renderer will be applied: {e}",
                level=1,
                func=inspect.stack()[0][3],
                plugin=plugin.dockwidget,
            )

            return get_raster_colors(
                layer,
                rasterBandVals,
                rasterBandNoDataVal,
                rasterBandMinVal,
                rasterBandMaxVal,
                None,
                plugin,
            )

    else:  # greyscale
        if rendererType != "singlebandgray":
            logToUser(
                f"Raster renderer type {rendererType} is not supported, default renderer will be applied",
                level=1,
                func=inspect.stack()[0][3],
            )
        pixMin = rasterBandMinVal[0]
        pixMax = rasterBandMaxVal[0]
        vals_range = pixMax - pixMin

        list_colors: List[int] = [
            (
                (255 << 24)
                | (int(255 * (rasterBandVals[0][ind] - pixMin) / vals_range) << 16)
                | (int(255 * (rasterBandVals[0][ind] - pixMin) / vals_range) << 8)
                | int(255 * (rasterBandVals[0][ind] - pixMin) / vals_range)
                if rasterBandVals[0][ind] != rasterBandNoDataVal[0]
                else (0 << 24) + (0 << 16) + (0 << 8) + 0
            )
            for ind, _ in enumerate(rasterBandVals[0])
            for _ in range(4)
        ]

    return list_colors, have_transparent_cells


def get_vertices_height(
    vertices_filtered: List[float],
    xy_z_values: dict,
    vertices_list_index: int,
    height_array,
    indices: tuple,
):
    index1, index1_0, index2, index2_0 = indices
    # top vertices ######################################
    try:
        z1 = xy_z_values[
            (
                vertices_filtered[vertices_list_index],
                vertices_filtered[vertices_list_index + 1],
            )
        ]
    except KeyError:
        if index1 > 0 and index2 > 0:
            z1 = height_array[index1_0][index2_0]
        elif index1 > 0:
            z1 = height_array[index1_0][index2]
        elif index2 > 0:
            z1 = height_array[index1][index2_0]
        else:
            z1 = height_array[index1][index2]

        if z1 is not None:
            xy_z_values[
                (
                    vertices_filtered[vertices_list_index],
                    vertices_filtered[vertices_list_index + 1],
                )
            ] = z1

    #################### z4
    try:
        z4 = xy_z_values[
            (
                vertices_filtered[vertices_list_index + 9],
                vertices_filtered[vertices_list_index + 10],
            )
        ]
    except:
        if index1 > 0:
            z4 = height_array[index1_0][index2]
        else:
            z4 = height_array[index1][index2]

        if z4 is not None:
            xy_z_values[
                (
                    vertices_filtered[vertices_list_index + 9],
                    vertices_filtered[vertices_list_index + 10],
                )
            ] = z4

    # bottom vertices ######################################
    z3 = height_array[index1][index2]
    if z3 is not None:
        xy_z_values[
            (
                vertices_filtered[vertices_list_index + 6],
                vertices_filtered[vertices_list_index + 7],
            )
        ] = z3

    try:
        z2 = xy_z_values[
            (
                vertices_filtered[vertices_list_index + 3],
                vertices_filtered[vertices_list_index + 4],
            )
        ]
    except:
        if index2 > 0:
            z2 = height_array[index1][index2_0]
        else:
            z2 = height_array[index1][index2]
        if z2 is not None:
            xy_z_values[
                (
                    vertices_filtered[vertices_list_index + 3],
                    vertices_filtered[vertices_list_index + 4],
                )
            ] = z2
    return z1, z2, z3, z4


def get_raster_band_data(
    selectedLayer,
    ds,
    index,
    rasterBandNames,
    rasterBandNoDataVal,
    rasterBandVals,
    rasterBandMinVal,
    rasterBandMaxVal,
) -> List[float]:
    rasterBandNames.append(selectedLayer.bandName(index + 1))
    rb = ds.GetRasterBand(index + 1)

    # note: raster stats can be messed up and are not reliable (e.g. Min is larger than Max)
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
                noDataValNew if val == fakeNA else val for val in bandValsFlatFake
            ]  # replace all values corresponding to NoData value

        # if default val unaccessible and minimum val is too small
        elif (
            isinstance(defaultNoData, str) or defaultNoData is None
        ) and valMin < const:  # if there are extremely small values but default NA unaccessible
            noDataValNew = valMin
            rasterBandNoDataVal.append(noDataValNew)
            # replace fake NA with new NA
            bandValsFlat = [
                noDataValNew if val == fakeNA else val for val in bandValsFlatFake
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
    return bandValsFlat


def get_height_array_from_elevation_layer(elevationLayer):
    elevation_arrays, _, _, all_na = getRasterArrays(elevationLayer)
    if elevation_arrays is None:
        return None
    array_band = elevation_arrays[0]

    const = float(-1 * math.pow(10, 30))
    height_array = np.where(
        (array_band < const) | (array_band > -1 * const) | (array_band == all_na[0]),
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
            height_array = height_array[[isinstance(i, float) for i in height_array]]
    return height_array


def get_raster_reprojected_stats(
    project,
    projectCRS,
    selectedLayer,
    originX,
    originY,
    rasterResXY,
    rasterDimensions,
    dataStorage,
):
    # get 4 corners of raster
    raster_top_right = QgsPointXY(
        originX + rasterResXY[0] * rasterDimensions[0], originY
    )
    rasterOriginPoint = QgsPointXY(originX, originY)
    rasterMaxPt = QgsPointXY(
        originX + rasterResXY[0] * rasterDimensions[0],
        originY + rasterResXY[1] * rasterDimensions[1],
    )
    raster_bottom_left = QgsPointXY(
        originX,
        originY + rasterResXY[1] * rasterDimensions[1],
    )
    # reproject corners to the project CRS
    scale_factor_x = scale_factor_y = 1

    reprojected_top_right = raster_top_right
    reprojectedOriginPt = rasterOriginPoint
    reprojectedMaxPt = rasterMaxPt
    reprojected_bottom_left = raster_bottom_left

    if selectedLayer.crs() != projectCRS:
        reprojected_top_right = transform.transform(
            project, raster_top_right, selectedLayer.crs(), projectCRS
        )
        reprojectedOriginPt = transform.transform(
            project, rasterOriginPoint, selectedLayer.crs(), projectCRS
        )
        reprojectedMaxPt = transform.transform(
            project, rasterMaxPt, selectedLayer.crs(), projectCRS
        )
        reprojected_bottom_left = transform.transform(
            project, raster_bottom_left, selectedLayer.crs(), projectCRS
        )

        scale_factor_x = abs(
            (reprojected_top_right.x() - reprojectedOriginPt.x())
            / (raster_top_right.x() - rasterOriginPoint.x())
        )
        scale_factor_y = abs(
            (reprojected_top_right.y() - reprojectedMaxPt.y())
            / (raster_top_right.y() - rasterMaxPt.y())
        )

    rasterResXY_reprojected = [
        rasterResXY[0] * scale_factor_x,
        rasterResXY[1] * scale_factor_y,
    ]
    rasterDimensions_reprojected = (
        abs(
            round(
                (reprojected_top_right.x() - reprojectedOriginPt.x())
                / rasterResXY_reprojected[0]
            )
        ),
        abs(
            round(
                (reprojected_top_right.y() - reprojectedMaxPt.y())
                / rasterResXY_reprojected[1]
            )
        ),
    )

    # apply offsets to all 4 pts
    r"""
    x1, y1 = apply_pt_offsets_rotation_on_send(
        reprojectedOriginPt.x(), reprojectedOriginPt.y(), dataStorage
    )
    reprojectedOriginPt = QgsPointXY(x1, y1)

    x2, y2 = apply_pt_offsets_rotation_on_send(
        reprojected_top_right.x(), reprojected_top_right.y(), dataStorage
    )
    reprojected_top_right = QgsPointXY(x2, y2)

    x3, y3 = apply_pt_offsets_rotation_on_send(
        reprojectedMaxPt.x(), reprojectedMaxPt.y(), dataStorage
    )
    reprojectedMaxPt = QgsPointXY(x3, y3)

    x4, y4 = apply_pt_offsets_rotation_on_send(
        reprojected_bottom_left.x(), reprojected_bottom_left.y(), dataStorage
    )
    reprojected_bottom_left = QgsPointXY(x4, y4)
    """

    return (
        reprojected_top_right,
        reprojectedOriginPt,
        reprojectedMaxPt,
        reprojected_bottom_left,
        rasterResXY_reprojected,
        rasterDimensions_reprojected,
    )


def get_elevation_indices(
    texture_transform,
    rasterResXY,
    rasterResXY_reprojected,
    reprojectedOriginX,
    reprojectedOriginY,
    h,
    v,
    elevationResX,
    elevationResY,
    elevationOriginX,
    elevationOriginY,
    elevationSizeX,
    elevationSizeY,
):
    if texture_transform is True:  # texture
        # index1: index on y-scale
        posX, posY = getXYofArrayPoint(
            rasterResXY_reprojected,
            reprojectedOriginX,
            reprojectedOriginY,
            h,
            v,
        )

        index1, index2, _, _ = getArrayIndicesFromXY(
            (
                elevationResX,
                elevationResY,
                elevationOriginX,
                elevationOriginY,
                elevationSizeX,
                elevationSizeY,
                None,
                None,
            ),
            posX,
            posY,
        )

        index1_0, index2_0, _, _ = getArrayIndicesFromXY(
            (
                elevationResX,
                elevationResY,
                elevationOriginX,
                elevationOriginY,
                elevationSizeX,
                elevationSizeY,
                None,
                None,
            ),
            posX - rasterResXY[0],
            posY - rasterResXY[1],
        )
    else:  # elevation
        index1 = v
        index1_0 = v - 1
        index2 = h
        index2_0 = h - 1
    return index1, index1_0, index2, index2_0


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
        time0 = datetime.now()

        terrain_transform = isAppliedLayerTransformByKeywords(
            selectedLayer, ["elevation", "mesh"], ["texture"], dataStorage
        )
        texture_transform = isAppliedLayerTransformByKeywords(
            selectedLayer, ["texture"], [], dataStorage
        )
        if terrain_transform is True or texture_transform is True:
            b = GisTopography(units=dataStorage.currentUnits)

        rasterBandCount = selectedLayer.bandCount()
        rasterDimensions = [selectedLayer.width(), selectedLayer.height()]

        ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
        rasterResXY = [float(ds.GetGeoTransform()[1]), float(ds.GetGeoTransform()[5])]

        originX = ds.GetGeoTransform()[0]
        originY = ds.GetGeoTransform()[3]

        reprojected_raster_stats = get_raster_reprojected_stats(
            project,
            projectCRS,
            selectedLayer,
            originX,
            originY,
            rasterResXY,
            rasterDimensions,
            dataStorage,
        )
        (
            reprojected_top_right,
            reprojectedOriginPt,
            reprojectedMaxPt,
            reprojected_bottom_left,
            rasterResXY_reprojected,
            rasterDimensions_reprojected,
        ) = reprojected_raster_stats
        reprojectedOriginX, reprojectedOriginY = (
            reprojectedOriginPt.x(),
            reprojectedOriginPt.y(),
        )

        # fill band values
        rasterBandNoDataVal = []
        rasterBandMinVal = []
        rasterBandMaxVal = []
        rasterBandVals = []
        rasterBandNames = []
        for index in range(rasterBandCount):
            bandValsFlat = get_raster_band_data(
                selectedLayer,
                ds,
                index,
                rasterBandNames,
                rasterBandNoDataVal,
                rasterBandVals,
                rasterBandMinVal,
                rasterBandMaxVal,
            )
            b["@(10000)" + selectedLayer.bandName(index + 1) + "_values"] = (
                bandValsFlat  # [0:int(max_values/rasterBandCount)]
            )

        b.x_resolution = rasterResXY[0]
        b.y_resolution = rasterResXY[1]
        b.x_size = rasterDimensions[0]
        b.y_size = rasterDimensions[1]
        b.x_origin, b.y_origin = (originX, originY)

        b.band_count = rasterBandCount
        b.band_names = rasterBandNames
        b.noDataValue = rasterBandNoDataVal

        # creating a mesh
        xy_z_values: Dict[tuple, float] = {}
        #############################################################

        elevationLayer = None
        height_array = None

        if terrain_transform is True:  # same layer, copy props
            elevationLayer = selectedLayer
            elevationResX, elevationResY = rasterResXY_reprojected
            elevationOriginX, elevationOriginY = (
                reprojectedOriginPt.x(),
                reprojectedOriginPt.y(),
            )
            elevationSizeX, elevationSizeY = (
                rasterDimensions_reprojected[0],
                rasterDimensions_reprojected[1],
            )

        elif texture_transform is True:
            elevation_layer_original: "QgsRasterLayer" = getElevationLayer(dataStorage)

            if elevation_layer_original is None:
                elevationResX = elevationResY = elevationOriginX = elevationOriginY = (
                    elevationSizeX
                ) = elevationSizeY = None

                logToUser(
                    f"Elevation layer is not found. Texture transformation for layer '{selectedLayer.name()}' will not be applied",
                    level=1,
                    plugin=plugin.dockwidget,
                )
            else:
                # match elevation layer props to the reprojected SelectedLayer
                ds_elevation_original = gdal.Open(
                    elevation_layer_original.source(), gdal.GA_ReadOnly
                )

                elevation_original_dimensions = [
                    elevation_layer_original.width(),
                    elevation_layer_original.height(),
                ]
                elevation_original_ResXY = [
                    float(ds_elevation_original.GetGeoTransform()[1]),
                    float(ds_elevation_original.GetGeoTransform()[5]),
                ]
                elevation_original_originX = ds_elevation_original.GetGeoTransform()[0]
                elevation_original_originY = ds_elevation_original.GetGeoTransform()[3]

                reprojected_elevation_stats = get_raster_reprojected_stats(
                    project,
                    projectCRS,
                    elevation_layer_original,
                    elevation_original_originX,
                    elevation_original_originY,
                    elevation_original_ResXY,
                    elevation_original_dimensions,
                    dataStorage,
                )

                (
                    elevation_reprojected_top_right,
                    elevation_reprojectedOriginPt,
                    elevation_reprojectedMaxPt,
                    elevation_reprojected_bottom_left,
                    elevation_resXY_reprojected,
                    elevation_dimensions_reprojected,
                ) = reprojected_elevation_stats

                elevationOriginX = elevation_reprojectedOriginPt.x()
                elevationOriginY = elevation_reprojectedOriginPt.y()

                # overwrite resolution & dimension to match raster
                elevationResX, elevationResY = (
                    elevation_resXY_reprojected[0],
                    elevation_resXY_reprojected[1],
                )
                elevationSizeX, elevationSizeY = (
                    elevation_dimensions_reprojected[0],
                    elevation_dimensions_reprojected[1],
                )
                elevationLayer = elevation_layer_original
                #################

        if elevationLayer is not None:
            height_array = get_height_array_from_elevation_layer(elevationLayer)
            if height_array is None:
                logToUser(
                    f"Elevation layer is not found. Texture transformation for layer '{selectedLayer.name()}' will not be applied",
                    level=1,
                    plugin=plugin.dockwidget,
                )

        largeTransform = False
        if (
            texture_transform is True
            and height_array is not None
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
        array_z = []  # size is larger by 1 than the raster size, in both dimensions

        faces_filtered = []
        colors_filtered = []
        vertices_filtered = []

        # construct mesh
        band1_values = rasterBandVals[0]
        list_nested = [
            (4, 4 * ind, 4 * ind + 1, 4 * ind + 2, 4 * ind + 3)
            for ind, _ in enumerate(band1_values)
        ]
        faces_filtered = [item for sublist in list_nested for item in sublist]
        vertices_filtered = get_raster_mesh_coords(
            reprojected_raster_stats,
            rasterResXY_reprojected,
            band1_values,
            dataStorage,
        )
        rendererType = selectedLayer.renderer().type()
        colors_filtered, have_transparent_cells = get_raster_colors(
            selectedLayer,
            rasterBandVals,
            rasterBandNoDataVal,
            rasterBandMinVal,
            rasterBandMaxVal,
            rendererType,
            plugin,
        )
        ###############################################################################
        if texture_transform is True or terrain_transform is True:
            for v in range(rasterDimensions[1]):  # each row, Y
                if largeTransform is True:
                    show_progress(v, rasterDimensions[1], selectedLayer.name(), plugin)

                row_z = []
                row_z_bottom = []
                for h in range(rasterDimensions[0]):  # item in a row, X
                    vertices_list_index = 3 * 4 * (v * rasterDimensions[0] + h)
                    colors_list_index = 4 * (v * rasterDimensions[0] + h)

                    z1 = z2 = z3 = z4 = 0
                    index1 = index1_0 = None

                    #############################################################
                    if height_array is not None:
                        index1, index1_0, index2, index2_0 = get_elevation_indices(
                            texture_transform,
                            rasterResXY,
                            rasterResXY_reprojected,
                            reprojectedOriginX,
                            reprojectedOriginY,
                            h,
                            v,
                            elevationResX,
                            elevationResY,
                            elevationOriginX,
                            elevationOriginY,
                            elevationSizeX,
                            elevationSizeY,
                        )
                        if index1 is None or index1_0 is None:
                            z1 = z2 = z3 = z4 = np.nan
                        else:
                            z1, z2, z3, z4 = get_vertices_height(
                                vertices_filtered,
                                xy_z_values,
                                vertices_list_index,
                                height_array,
                                (index1, index1_0, index2, index2_0),
                            )

                        ### height list to smoothen later:
                        if h == 0:
                            row_z.append(z1)
                            row_z_bottom.append(z2)
                        row_z.append(z4)
                        row_z_bottom.append(z3)

                    # color vertices according to QGIS renderer
                    if height_array is not None and (
                        index1 is None or index1_0 is None
                    ):  # transparent color
                        colors_filtered[colors_list_index] = colors_filtered[
                            colors_list_index + 1
                        ] = colors_filtered[colors_list_index + 2] = colors_filtered[
                            colors_list_index + 3
                        ] = (
                            (0 << 24) + (0 << 16) + (0 << 8) + 0
                        )

                if terrain_transform is True or texture_transform is True:
                    if v == 0:
                        array_z.append(row_z)
                    array_z.append(row_z_bottom)

        ## smoothen z-values
        if (
            (terrain_transform is True or texture_transform is True)
            and len(row_z) > 2
            and len(array_z) > 2
        ):
            array_z_nans = np.array(array_z)

            array_z_filled = np.array(array_z)
            mask = np.isnan(array_z_filled)
            array_z_filled[mask] = np.interp(
                np.flatnonzero(mask), np.flatnonzero(~mask), array_z_filled[~mask]
            )

            sigma = 0.8  # for elevation
            if texture_transform is True:
                sigma = 1  # for texture

            gaussian_array = sp.ndimage.filters.gaussian_filter(
                array_z_filled, sigma, mode="nearest"
            )

            # update vertices_filtered with z-value
            for v in range(rasterDimensions[1]):  # each row, Y
                for h in range(rasterDimensions[0]):  # item in a row, X
                    vertices_list_index = 3 * 4 * (v * rasterDimensions[0] + h)
                    if not np.isnan(array_z_nans[v][h]):
                        vertices_filtered[vertices_list_index + 2] = gaussian_array[v][
                            h
                        ]
                        vertices_filtered[vertices_list_index + 5] = gaussian_array[
                            v + 1
                        ][h]
                        vertices_filtered[vertices_list_index + 8] = gaussian_array[
                            v + 1
                        ][h + 1]
                        vertices_filtered[vertices_list_index + 11] = gaussian_array[v][
                            h + 1
                        ]

        # apply offset & rotation
        vertices_filtered2 = apply_offset_rotation_to_vertices_send(
            vertices_filtered, dataStorage
        )

        # delete faces using invisible vertices
        if have_transparent_cells is True:
            vertices_filtered_removed = []
            colors_filtered_removed = []
            deleted_vert = []
            vertex_remapping = {}

            for i, color in enumerate(colors_filtered):
                if i % 4 != 0:  # only look a the first vertex of a square
                    if vertex_remapping[i - 1] is None:
                        vertex_remapping[i] = None
                        deleted_vert.append(i)
                    else:
                        vertex_remapping[i] = vertex_remapping[i - 1] + 1
                    continue
                a, _, _, _ = get_a_r_g_b(color)
                if a != 0:
                    colors_filtered_removed.extend(colors_filtered[i : i + 4])
                    vertices_filtered_removed.extend(
                        vertices_filtered2[3 * i : 3 * i + 12]
                    )
                    vertex_remapping[i] = i - len(deleted_vert)
                else:
                    deleted_vert.append(i)
                    vertex_remapping[i] = None

            faces_filtered_removed = []
            count = 0
            for f in faces_filtered:
                if count >= len(faces_filtered):
                    break
                # get first vertex color:
                if vertex_remapping[faces_filtered[count + 1]] is not None:
                    faces_filtered_removed.append(4)
                    faces_filtered_removed.append(
                        vertex_remapping[faces_filtered[count + 1]]
                    )
                    faces_filtered_removed.append(
                        vertex_remapping[faces_filtered[count + 2]]
                    )
                    faces_filtered_removed.append(
                        vertex_remapping[faces_filtered[count + 3]]
                    )
                    faces_filtered_removed.append(
                        vertex_remapping[faces_filtered[count + 4]]
                    )
                count += 5
        else:
            vertices_filtered_removed = vertices_filtered2.copy()
            colors_filtered_removed = colors_filtered.copy()
            faces_filtered_removed = faces_filtered.copy()

        mesh = constructMeshFromRaster(
            vertices_filtered_removed,  # vertices_filtered2,
            faces_filtered_removed,  # faces_filtered,
            colors_filtered_removed,  # colors_filtered,
            dataStorage,
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

        time1 = datetime.now()
        print(f"Time to convert Raster: {(time1-time0).total_seconds()} sec")
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
                if (
                    isinstance(feature, GisFeature)
                    and isinstance(speckle_geom[0], GisPolygonGeometry)
                    and speckle_geom[0].boundary is None
                ):
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
