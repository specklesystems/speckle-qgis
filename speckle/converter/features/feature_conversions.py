from datetime import datetime
import inspect
import math
import os
from typing import Dict, List, Union

import numpy as np
import hashlib

import scipy as sp
from plugin_utils.helpers import (
    findOrCreatePath,
    get_scale_factor,
    get_scale_factor_to_meter,
)
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

        if geomType == "None":
            geom = GisNonGeometryElement()
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
                                all_errors += (
                                    "Polygon display mesh is simplified" + ", "
                                )
                                logToUser(
                                    "Polygon display mesh is simplified",
                                    level=1,
                                    func=inspect.stack()[0][3],
                                )

                    if len(geom.geometry) == 0:
                        all_errors = "No geometry converted"
                    new_report.update(
                        {"obj_type": geom.speckle_type, "errors": all_errors}
                    )

                else:  # geom is None
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

        dataStorage.latestActionFeaturesReport[
            len(dataStorage.latestActionFeaturesReport) - 1
        ].update(new_report)
        return geom

    except Exception as e:
        new_report.update({"errors": e})
        dataStorage.latestActionFeaturesReport[
            len(dataStorage.latestActionFeaturesReport) - 1
        ].update(new_report)
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return geom


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
    path = (
        os.path.expandvars(r"%LOCALAPPDATA%")
        + "\\Temp\\Speckle_QGIS_temp\\"
        + datetime.now().strftime("%Y-%m-%d_%H-%M")
    )
    findOrCreatePath(path)

    out = path + "\\out.tif"
    options = gdal.WarpOptions(
        xRes=resolutionX, yRes=resolutionY, srcSRS=layer.crs(), dstSRS=crs
    )
    gdal.Warp(out, layer.source(), options=options)
    return QgsRasterLayer(out, "", "gdal")


def get_raster_mesh_coords(
    reprojectedOriginPt,
    reprojectedMaxPt,
    rasterResXY: list,
    rasterDimensions: list,
    band1_values: list,
    dataStorage,
) -> List[float]:
    xOrigin = reprojectedOriginPt.x()
    yOrigin = reprojectedOriginPt.y()
    list_nested = [
        (
            xOrigin + rasterResXY[0] * (ind % rasterDimensions[0]),
            yOrigin + rasterResXY[1] * math.floor(ind / rasterDimensions[0]),
            0,
            xOrigin + rasterResXY[0] * (ind % rasterDimensions[0]),
            yOrigin + rasterResXY[1] * (math.floor(ind / rasterDimensions[0]) + 1),
            0,
            xOrigin + rasterResXY[0] * (ind % rasterDimensions[0] + 1),
            yOrigin + rasterResXY[1] * math.floor(ind / rasterDimensions[0] + 1),
            0,
            xOrigin + rasterResXY[0] * (ind % rasterDimensions[0] + 1),
            yOrigin + rasterResXY[1] * math.floor(ind / rasterDimensions[0]),
            0,
        )
        for ind, _ in enumerate(band1_values)
    ]
    list_flattened = [item for sublist in list_nested for item in sublist]

    return list_flattened


def apply_offset_rotation_to_vertices_send(vertices: List[float], dataStorage):
    for index in range(int(len(vertices) / 3)):
        x, y = apply_pt_offsets_rotation_on_send(
            vertices[index], vertices[index + 1], dataStorage
        )
        vertices[index] = x
        vertices[index + 1] = y


def get_raster_colors(
    rasterBandVals,
    rasterBandNoDataVal,
    rasterBandMinVal,
    rasterBandMaxVal,
    rendererType,
):
    list_colors = []
    if len(rasterBandVals) == 3 or len(rasterBandVals) == 4:  # RGB

        vals_range0 = rasterBandMaxVal[0] - rasterBandMinVal[0]
        vals_range1 = rasterBandMaxVal[1] - rasterBandMinVal[1]
        vals_range2 = rasterBandMaxVal[2] - rasterBandMinVal[2]

        list_colors = [
            (
                (255 << 24)
                | (
                    255
                    * (int(rasterBandVals[0][ind] - rasterBandMinVal[0]) / vals_range0)
                    << 16
                )
                | (
                    255
                    * (int(rasterBandVals[1][ind] - rasterBandMinVal[1]) / vals_range1)
                    << 8
                )
                | 255
                * (int(rasterBandVals[2][ind] - rasterBandMinVal[2]) / vals_range2)
                if (
                    rasterBandVals[0][ind] != rasterBandNoDataVal[0]
                    and rasterBandVals[1][ind] != rasterBandNoDataVal[1]
                    and rasterBandVals[2][ind] != rasterBandNoDataVal[2]
                )
                else (0 << 24) + (0 << 16) + (0 << 8) + 0
            )
            for ind, _ in enumerate(rasterBandVals[0])
            for _ in range(4)
        ]
    else:  # greyscale
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
    """
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
                    (255 << 24)
                    + (rgb[0] << 16)
                    + (rgb[1] << 8)
                    + rgb[2]
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
                    (255 << 24)
                    + (rgb[0] << 16)
                    + (rgb[1] << 8)
                    + rgb[2]
                )
                break
        if value == rasterBandNoDataVal[bandIndex]:
            alpha = 0
            color = (alpha << 24) + (0 << 16) + (0 << 8) + 0
    """
    return list_colors


def add_vertices_height(
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
    except:
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
        rasterBandNames = []
        rasterDimensions = [selectedLayer.width(), selectedLayer.height()]

        ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
        rasterResXY = [float(ds.GetGeoTransform()[1]), float(ds.GetGeoTransform()[5])]

        originX = ds.GetGeoTransform()[0]
        originY = ds.GetGeoTransform()[3]
        rasterOriginPoint = QgsPointXY(originX, originY)
        rasterMaxPt = QgsPointXY(
            originX + rasterResXY[0] * rasterDimensions[0],
            originY + rasterResXY[1] * rasterDimensions[1],
        )

        # reproject raster TODO
        # raster_reprojected = reproject_raster(
        #    selectedLayer, projectCRS, rasterResXY[0], rasterResXY[1]
        # )
        reprojectedOriginPt = rasterOriginPoint
        reprojectedMaxPt = rasterMaxPt
        scale_factor = 1

        if selectedLayer.crs() != projectCRS:
            reprojectedOriginPt = transform.transform(
                project, rasterOriginPoint, selectedLayer.crs(), projectCRS
            )
            reprojectedMaxPt = transform.transform(
                project, rasterMaxPt, selectedLayer.crs(), projectCRS
            )
            scale_factor = get_scale_factor(
                str(QgsUnitTypes.encodeUnit(selectedLayer.crs().mapUnits())),
                dataStorage,
            )

        rasterResXY_reprojected = [
            rasterResXY[0] * scale_factor,
            rasterResXY[1] * scale_factor,
        ]

        # fill band values
        rasterBandNoDataVal = []
        rasterBandMinVal = []
        rasterBandMaxVal = []
        rasterBandVals = []
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
        b.x_origin, b.y_origin = apply_pt_offsets_rotation_on_send(
            reprojectedOriginPt.x(), reprojectedOriginPt.y(), dataStorage
        )
        b.band_count = rasterBandCount
        b.band_names = rasterBandNames
        b.noDataValue = rasterBandNoDataVal

        # creating a mesh
        xy_z_values: Dict[tuple, float] = {}
        #############################################################

        elevationLayer = None
        elevationProj = None
        if texture_transform is True:
            elevationLayer = getElevationLayer(dataStorage)
        elif terrain_transform is True:
            elevationLayer = selectedLayer

        if elevationLayer is not None:
            elevationLayer = reproject_raster(
                elevationLayer, selectedLayer.crs(), rasterResXY[0], rasterResXY[1]
            )
            settings_elevation_layer = get_raster_stats(elevationLayer)
            (
                elevationResX,
                elevationResY,
                elevationOriginX,
                elevationOriginY,
                elevationSizeX,
                elevationSizeY,
                _,
                elevationProj,
            ) = settings_elevation_layer

            elevation_arrays, _, _, all_na = getRasterArrays(elevationLayer)
            array_band = elevation_arrays[0]

            const = float(-1 * math.pow(10, 30))
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
            elevation_arrays = all_na = None
            elevationResX = elevationResY = elevationOriginX = elevationOriginY = (
                elevationSizeX
            ) = elevationSizeY = None
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
            reprojectedOriginPt,
            reprojectedMaxPt,
            rasterResXY_reprojected,
            rasterDimensions,
            band1_values,
            dataStorage,
        )
        rendererType = selectedLayer.renderer().type()
        colors_filtered = get_raster_colors(
            rasterBandVals,
            rasterBandNoDataVal,
            rasterBandMinVal,
            rasterBandMaxVal,
            rendererType,
        )
        ###############################################################################
        if texture_transform is True or terrain_transform is True:
            for v in range(rasterDimensions[1]):  # each row, Y
                if largeTransform is True:
                    show_progress(v, rasterDimensions[1], selectedLayer.name(), plugin)

                row_z = []
                row_z_bottom = []
                for h in range(rasterDimensions[0]):  # item in a row, X
                    vertices_list_index = 3 * 4 * (v * rasterDimensions[1] + h)
                    colors_list_index = 4 * (v * rasterDimensions[1] + h)

                    z1 = z2 = z3 = z4 = 0
                    index1 = index1_0 = None

                    #############################################################
                    if height_array is not None:
                        if texture_transform is True:  # texture
                            # index1: index on y-scale
                            posX, posY = getXYofArrayPoint(
                                rasterResXY_reprojected,
                                originX_reprojected,
                                originY_reprojected,
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
                            z1 = z2 = z3 = z4 = np.nan
                        else:
                            z1, z2, z3, z4 = add_vertices_height(
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

            for v in range(rasterDimensions[1]):  # each row, Y
                for h in range(rasterDimensions[0]):  # item in a row, X
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
        apply_offset_rotation_to_vertices_send(vertices_filtered, dataStorage)

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

        if isinstance(feature, GisNonGeometryElement):
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
                if len(speckle_geom) == 1:
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
