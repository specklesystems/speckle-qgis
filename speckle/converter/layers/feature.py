from distutils.log import error
import inspect
import math
from tokenize import String
from typing import List
from qgis._core import (QgsCoordinateTransform, Qgis, QgsPointXY, QgsGeometry, QgsRasterBandStats, QgsFeature, QgsFields, 
    QgsField, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem, QgsProject,
    QgsUnitTypes )
from specklepy.objects import Base

from typing import Dict, Any

from PyQt5.QtCore import QVariant, QDate, QDateTime
from speckle.converter import geometry
from speckle.converter.geometry import convertToSpeckle, transform
from specklepy.objects.GIS.geometry import GisRasterElement
from speckle.converter.geometry.mesh import constructMesh, constructMeshFromRaster
from specklepy.objects.GIS.layers import RasterLayer
from speckle.utils.panel_logging import logger
from speckle.converter.layers.utils import get_raster_stats, get_scale_factor_to_meter, getArrayIndicesFromXY, getElevationLayer, getHeightWithRemainderFromArray, getRasterArrays, getVariantFromValue, getXYofArrayPoint, isAppliedLayerTransformByKeywords, traverseDict, validateAttributeName 
from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)
import numpy as np 
import scipy as sp
import scipy.ndimage

from pyqt_ui.logger import logToUser

def featureToSpeckle(fieldnames: List[str], f: QgsFeature, sourceCRS: QgsCoordinateReferenceSystem, targetCRS: QgsCoordinateReferenceSystem, project: QgsProject, selectedLayer: QgsVectorLayer or QgsRasterLayer, dataStorage = None):

    if dataStorage is None: return 
    units = dataStorage.currentUnits
    try:
        geom = None
        #apply transformation if needed
        if sourceCRS != targetCRS:
            xform = QgsCoordinateTransform(sourceCRS, targetCRS, project)
            geometry = f.geometry()
            geometry.transform(xform)
            f.setGeometry(geometry)

        # Try to extract geometry
        try:
            geom = convertToSpeckle(f, selectedLayer, dataStorage)
            
            #b.geometry = [] 
            attributes = Base()
            if geom is not None and geom!="None": 
                if isinstance(geom.geometry, List):

                    for g in geom.geometry:
                        if g is not None and g!="None": 
                            pass
                        else:
                            logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
                            print(g)
            else: 
                logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
                print(geom)
        
        except Exception as error:
            logToUser("Error converting geometry: " + str(error), level = 2, func = inspect.stack()[0][3])

        for name in fieldnames: 
            corrected = validateAttributeName(name, fieldnames)
            f_name = f[name]
            if f_name == "NULL" or f_name is None or str(f_name) == "NULL": f_name = None
            if isinstance(f[name], list): 
                x = ""
                for i, attr in enumerate(f[name]): 
                    if i==0: x += str(attr)
                    else: x += ", " + str(attr)
                f_name = x 
            attributes[corrected] = f_name
        if geom is not None and geom!="None":
            geom.attributes = attributes
        return geom
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return geom
          
def bimFeatureToNative(exist_feat: QgsFeature, feature: Base, fields: QgsFields, crs, path: str, dataStorage = None):
    print("04_________BIM Feature To Native____________")
    try:
        exist_feat.setFields(fields)  

        feat_updated = updateFeat(exist_feat, fields, feature)
        #print(fields.toList())
        #print(feature)
        #print(feat_updated)

        return feat_updated
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return 

def addFeatVariant(key, variant, value, f: QgsFeature):
    #print("__________add variant")
    try:
        feat = f
        
        r'''
        if isinstance(value, str) and variant == QVariant.Date:  # 14
            y,m,d = value.split("(")[1].split(")")[0].split(",")[:3]
            value = QDate(int(y), int(m), int(d) ) 
        elif isinstance(value, str) and variant == QVariant.DateTime: 
            y,m,d,t1,t2 = value.split("(")[1].split(")")[0].split(",")[:5]
            value = QDateTime(int(y), int(m), int(d), int(t1), int(t2) )
        '''
        if variant == 10: value = str(value) # string

        if value != "NULL" and value != "None":
            if variant == getVariantFromValue(value): 
                feat[key] = value
            elif isinstance(value, float) and variant == 4: #float, but expecting Long (integer)
                feat[key] = int(value) 
            elif isinstance(value, int) and variant == 6: #int (longlong), but expecting float 
                feat[key] = float(value) 
            else: 
                feat[key] = None 
                #print(key); print(value); print(type(value)); print(variant); print(getVariantFromValue(value))
        elif isinstance(variant, int): feat[key] = None
        return feat 
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return 

def updateFeat(feat: QgsFeature, fields: QgsFields, feature: Base) -> dict[str, Any]:
    try:
        for i, key in enumerate(fields.names()): 
            variant = fields.at(i).type()
            try:
                if key == "Speckle_ID": 
                    value = str(feature["id"])
                    #if key != "parameters": print(value)
                    feat[key] = value 

                    feat = addFeatVariant(key, variant, value, feat)

                else:
                    try: 
                        value = feature[key] 
                        feat = addFeatVariant(key, variant, value, feat)

                    except:
                        value = None
                        rootName = key.split("_")[0]
                        #try: # if the root category exists
                        # if its'a list 
                        if isinstance(feature[rootName], list):
                            for i in range(len(feature[rootName])):
                                try:
                                    newF, newVals = traverseDict({}, {}, rootName + "_" + str(i), feature[rootName][i])
                                    for i, (key,value) in enumerate(newVals.items()):
                                        for k, (x,y) in enumerate(newF.items()):
                                            if key == x: variant = y; break
                                        feat = addFeatVariant(key, variant, value, feat)
                                except Exception as e: print(e)
                        #except: # if not a list
                        else:
                            try:
                                newF, newVals = traverseDict({}, {}, rootName, feature[rootName])
                                for i, (key,value) in enumerate(newVals.items()):
                                    for k, (x,y) in enumerate(newF.items()):
                                        if key == x: variant = y; break
                                    feat = addFeatVariant(key, variant, value, feat)
                            except Exception as e: feat.update({key: None})
            except Exception as e: 
                feat[key] = None
        #feat_sorted = {k: v for k, v in sorted(feat.items(), key=lambda item: item[0])}
        #print("_________________end of updating a feature_________________________")
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])

    return feat 


def rasterFeatureToSpeckle(selectedLayer: QgsRasterLayer, projectCRS:QgsCoordinateReferenceSystem, project: QgsProject, plugin ) -> Base:
    
    dataStorage = plugin.dataStorage
    if dataStorage is None: return

    b = GisRasterElement(units = dataStorage.currentUnits)
    try:
        rasterBandCount = selectedLayer.bandCount()
        rasterBandNames = []
        rasterDimensions = [selectedLayer.width(), selectedLayer.height()]
        #if rasterDimensions[0]*rasterDimensions[1] > 1000000 :
        #   logToUser("Large layer: ", level = 1, func = inspect.stack()[0][3])

        ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
        originX = ds.GetGeoTransform()[0]
        originY = ds.GetGeoTransform()[3]
        rasterOriginPoint = QgsPointXY(originX, originY)
        rasterResXY = [float(ds.GetGeoTransform()[1]), float(ds.GetGeoTransform()[5])]
        rasterWkt = ds.GetProjection() 
        rasterProj = QgsCoordinateReferenceSystem.fromWkt(rasterWkt).toProj().replace(" +type=crs","")
        rasterBandNoDataVal = []
        rasterBandMinVal = []
        rasterBandMaxVal = []
        rasterBandVals = []

        # Try to extract geometry
        reprojectedPt = QgsGeometry.fromPointXY(QgsPointXY())
        try:
            reprojectedPt = rasterOriginPoint
            if selectedLayer.crs()!= projectCRS: 
                reprojectedPt = transform.transform(project, rasterOriginPoint, selectedLayer.crs(), projectCRS)
        except Exception as error:
            #logToUser("Error converting point geometry: " + str(error), level = 2, func = inspect.stack()[0][3])
            logToUser("Error converting point geometry: " + str(error), level = 2)
        
        for index in range(rasterBandCount):
            rasterBandNames.append(selectedLayer.bandName(index+1))
            rb = ds.GetRasterBand(index+1)
            valMin = selectedLayer.dataProvider().bandStatistics(index+1, QgsRasterBandStats.All).minimumValue
            valMax = selectedLayer.dataProvider().bandStatistics(index+1, QgsRasterBandStats.All).maximumValue
            bandVals = rb.ReadAsArray().tolist()

            bandValsFlat = []
            [bandValsFlat.extend(item) for item in bandVals]
            #look at mesh chunking

            const = float(-1* math.pow(10,30))
            defaultNoData = rb.GetNoDataValue()
            #print(type(rb.GetNoDataValue()))

            # check whether NA value is too small or raster has too small values
            # assign min value of an actual list; re-assign NA val; replace list items to new NA val
            try:
                # create "safe" fake NA value; replace extreme values with it
                fakeNA = max(bandValsFlat) + 1 
                bandValsFlatFake = [fakeNA if val<=const else val for val in bandValsFlat] # replace all values corresponding to NoData value 
                
                #if default NA value is too small
                if (isinstance(defaultNoData, float) or isinstance(defaultNoData, int)) and defaultNoData < const:
                    # find and rewrite min of actual band values; create new NA value
                    valMin = min(bandValsFlatFake)
                    noDataValNew = valMin - 1000 # use new adequate value
                    rasterBandNoDataVal.append(noDataValNew)
                    # replace fake NA with new NA
                    bandValsFlat = [noDataValNew if val == fakeNA else val for val in bandValsFlatFake] # replace all values corresponding to NoData value 
                
                # if default val unaccessible and minimum val is too small 
                elif (isinstance(defaultNoData, str) or defaultNoData is None) and valMin < const: # if there are extremely small values but default NA unaccessible 
                    noDataValNew = valMin 
                    rasterBandNoDataVal.append(noDataValNew)
                    # replace fake NA with new NA
                    bandValsFlat = [noDataValNew if val == fakeNA else val for val in bandValsFlatFake] # replace all values corresponding to NoData value 
                    # last, change minValto actual one
                    valMin = min(bandValsFlatFake)

                else: rasterBandNoDataVal.append(rb.GetNoDataValue())

            except: rasterBandNoDataVal.append(rb.GetNoDataValue())

            
            rasterBandVals.append(bandValsFlat)
            rasterBandMinVal.append(valMin)
            rasterBandMaxVal.append(valMax)
            b["@(10000)" + selectedLayer.bandName(index+1) + "_values"] = bandValsFlat #[0:int(max_values/rasterBandCount)]

        b.x_resolution = rasterResXY[0]
        b.y_resolution = rasterResXY[1]
        b.x_size = rasterDimensions[0]
        b.y_size = rasterDimensions[1]
        b.x_origin = reprojectedPt.x()
        b.y_origin = reprojectedPt.y() 
        b.band_count = rasterBandCount
        b.band_names = rasterBandNames
        b.noDataValue = rasterBandNoDataVal
        # creating a mesh
        count = 0
        rendererType = selectedLayer.renderer().type()

        xy_list = []
        z_list = []
        #print(rendererType)
        # identify symbology type and if Multiband, which band is which color

        ############################################################# 
        terrain_transform = False
        texture_transform = False
        #height_list = rasterBandVals[0]          
        terrain_transform = isAppliedLayerTransformByKeywords(selectedLayer, ["elevation", "mesh"], ["texture"], dataStorage)
        texture_transform = isAppliedLayerTransformByKeywords(selectedLayer, ["texture"], [], dataStorage)

        elevationLayer = None 
        elevationProj = None 
        if texture_transform is True:
            elevationLayer = getElevationLayer(dataStorage) 
        elif terrain_transform is True:
            elevationLayer = selectedLayer
        if elevationLayer is not None:
            elevation_arrays, all_mins, all_maxs, all_na = getRasterArrays(elevationLayer)
            array_band = elevation_arrays[0]
            settings_elevation_layer = get_raster_stats(elevationLayer)
            elevationResX, elevationResY, elevationOriginX, elevationOriginY, elevationSizeX, elevationSizeY, elevationWkt, elevationProj = settings_elevation_layer
            height_array = np.where( (array_band < const) | (array_band > -1*const) | (array_band == all_na[0]), np.nan, array_band)
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
        
        else:
            elevation_arrays = all_mins = all_maxs = all_na = None
            elevationResX = elevationResY = elevationOriginX = elevationOriginY = elevationSizeX = elevationSizeY = elevationWkt = None
            height_array = None
            
        if texture_transform is True and elevationLayer is None:
            logToUser(f"Elevation layer is not found. Texture transformation for layer '{selectedLayer.name()}' will not be applied", level = 1, plugin = plugin.dockwidget)
        elif texture_transform is True and rasterDimensions[1]*rasterDimensions[0]>=10000 and elevationProj is not None and rasterProj is not None and elevationProj != rasterProj:
            # warning if >= 100x100 raster is being projected to an elevation with different CRS 
            logToUser(f"Texture transformation for the layer '{selectedLayer.name()}' might take a while 🕒", level = 0, plugin = plugin.dockwidget)
        elif texture_transform is True and rasterDimensions[1]*rasterDimensions[0]>=250000:
            # warning if >= 500x500 raster is being projected to any elevation 
            logToUser(f"Texture transformation for the layer '{selectedLayer.name()}' might take a while 🕒", level = 0, plugin = plugin.dockwidget)
        ############################################################
        faces_array = []
        colors_array = []
        vertices_array = []
        array_z = [] # size is large by 1 than the raster size, in both dimensions 
        for v in range(rasterDimensions[1] ): #each row, Y
            vertices = []
            faces = []
            colors = []
            row_z = []
            row_z_bottom = []
            for h in range(rasterDimensions[0] ): #item in a row, X
                pt1 = QgsPointXY(rasterOriginPoint.x()+h*rasterResXY[0], rasterOriginPoint.y()+v*rasterResXY[1])
                pt2 = QgsPointXY(rasterOriginPoint.x()+h*rasterResXY[0], rasterOriginPoint.y()+(v+1)*rasterResXY[1])
                pt3 = QgsPointXY(rasterOriginPoint.x()+(h+1)*rasterResXY[0], rasterOriginPoint.y()+(v+1)*rasterResXY[1])
                pt4 = QgsPointXY(rasterOriginPoint.x()+(h+1)*rasterResXY[0], rasterOriginPoint.y()+v*rasterResXY[1])
                # first, get point coordinates with correct position and resolution, then reproject each:
                if selectedLayer.crs()!= projectCRS:
                    pt1 = transform.transform(project, src = pt1, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
                    pt2 = transform.transform(project, src = pt2, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
                    pt3 = transform.transform(project, src = pt3, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
                    pt4 = transform.transform(project, src = pt4, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
                
                z1 = z2 = z3 = z4 = 0
                index1 = index1_0 = None
        
                ############################################################# 
                if (terrain_transform is True or texture_transform is True) and height_array is not None:
                    if texture_transform is True: # texture 
                        # index1: index on y-scale 
                        posX, posY = getXYofArrayPoint((rasterResXY[0], rasterResXY[1], originX, originY, rasterDimensions[1], rasterDimensions[0], rasterWkt, rasterProj), h, v, elevationWkt, elevationProj)
                        index1, index2, remainder1, remainder2 = getArrayIndicesFromXY((elevationResX, elevationResY, elevationOriginX, elevationOriginY, elevationSizeX, elevationSizeY, elevationWkt, elevationProj), posX, posY )
                        index1_0, index2_0, remainder1_0, remainder2_0 = getArrayIndicesFromXY((elevationResX, elevationResY, elevationOriginX, elevationOriginY, elevationSizeX, elevationSizeY, elevationWkt, elevationProj), posX-rasterResXY[0], posY-rasterResXY[1] )
                    else: # elevation 
                        index1 = v
                        index1_0 = v-1
                        index2 = h
                        index2_0 = h-1

                    if index1 is None or index1_0 is None: 
                        #count += 4
                        #continue # skip the pixel
                        z1 = z2 = z3 = z4 = np.nan 
                    else: 
                        # top vertices ######################################
                        try:
                            z1 = z_list[ xy_list.index((pt1.x(), pt1.y())) ]
                        except:
                            if index1>0 and index2>0:
                                z1 = getHeightWithRemainderFromArray(height_array, texture_transform, index1_0, index2_0)
                            elif index1>0:
                                z1 = getHeightWithRemainderFromArray(height_array, texture_transform, index1_0, index2)
                            elif index2>0:
                                z1 = getHeightWithRemainderFromArray(height_array, texture_transform, index1, index2_0)
                            else:
                                z1 = getHeightWithRemainderFromArray(height_array, texture_transform, index1, index2)
                            
                            if z1 is not None: 
                                z_list.append(z1)
                                xy_list.append((pt1.x(), pt1.y()))
                            
                        #################### z4 
                        try:
                            z4 = z_list[ xy_list.index((pt4.x(), pt4.y())) ]
                        except:
                            if index1>0:
                                z4 = getHeightWithRemainderFromArray(height_array, texture_transform, index1_0, index2)
                            else:
                                z4 = getHeightWithRemainderFromArray(height_array, texture_transform, index1, index2)
                        
                            if z4 is not None: 
                                z_list.append(z4)
                                xy_list.append((pt4.x(), pt4.y()))

                        # bottom vertices ######################################
                        z3 = getHeightWithRemainderFromArray(height_array, texture_transform, index1, index2)
                        if z3 is not None: 
                            z_list.append(z3)
                            xy_list.append((pt3.x(), pt3.y()))

                        try:
                            z2 = z_list[ xy_list.index((pt2.x(), pt2.y())) ]
                        except:
                            if index2>0:
                                z2 = getHeightWithRemainderFromArray(height_array, texture_transform, index1, index2_0)
                            else: 
                                z2 = getHeightWithRemainderFromArray(height_array, texture_transform, index1, index2)
                            if z2 is not None: 
                                z_list.append(z2)
                                xy_list.append((pt2.x(), pt2.y()))
                        
                        ##############################################
                    
                    max_len = rasterDimensions[0]*4 + 4
                    if len(z_list) > max_len:
                        z_list = z_list[len(z_list)-max_len:]
                        xy_list = xy_list[len(xy_list)-max_len:]
                    
                    ### list to smoothen later: 
                    if h==0: 
                        row_z.append(z1)
                        row_z_bottom.append(z2)
                    row_z.append(z4)
                    row_z_bottom.append(z3)

                ########################################################

                vertices.append([pt1.x(), pt1.y(), z1, pt2.x(), pt2.y(), z2, pt3.x(), pt3.y(), z3, pt4.x(), pt4.y(), z4]) ## add 4 points
                current_vertices = v*rasterDimensions[0]*4 + h*4 #len(np.array(faces_array).flatten()) * 4 / 5
                faces.append([4, current_vertices, current_vertices + 1, current_vertices + 2, current_vertices + 3])

                # color vertices according to QGIS renderer
                color = (255<<24) + (0<<16) + (0<<8) + 0
                noValColor = selectedLayer.renderer().nodataColor().getRgb() 

                colorLayer = selectedLayer
                currentRasterBandCount = rasterBandCount

                if (terrain_transform is True or texture_transform is True) and height_array is not None and (index1 is None or index1_0 is None): # transparent color
                    color = (0<<24) + (0<<16) + (0<<8) + 0
                elif rendererType == "multibandcolor": 
                    valR = 0
                    valG = 0
                    valB = 0
                    bandRed = int(colorLayer.renderer().redBand())
                    bandGreen = int(colorLayer.renderer().greenBand())
                    bandBlue = int(colorLayer.renderer().blueBand())

                    alpha = 255
                    for k in range(currentRasterBandCount): 

                        valRange = (rasterBandMaxVal[k] - rasterBandMinVal[k])
                        if valRange == 0: colorVal = 0
                        elif rasterBandVals[k][int(count/4)] == rasterBandNoDataVal[k]: 
                            colorVal = 0
                        #    alpha = 0
                        #   break
                        else: colorVal = int( (rasterBandVals[k][int(count/4)] - rasterBandMinVal[k]) / valRange * 255 )
                            
                        if k+1 == bandRed: valR = colorVal
                        if k+1 == bandGreen: valG = colorVal
                        if k+1 == bandBlue: valB = colorVal

                    color =  (alpha<<24) + (valR<<16) + (valG<<8) + valB 

                elif rendererType == "paletted":
                    bandIndex = colorLayer.renderer().band()-1 #int
                    #if textureLayer is not None:
                    #    value = texture_arrays[bandIndex][index1][index2] 
                    #else:
                    value = rasterBandVals[bandIndex][int(count/4)] #find in the list and match with color

                    rendererClasses = colorLayer.renderer().classes()
                    for c in range(len(rendererClasses)-1):
                        if value >= rendererClasses[c].value and value <= rendererClasses[c+1].value :
                            rgb = rendererClasses[c].color.getRgb()
                            color =  (255<<24) + (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
                            break

                elif rendererType == "singlebandpseudocolor":
                    bandIndex = colorLayer.renderer().band()-1 #int
                    #if textureLayer is not None:
                    #    value = texture_arrays[bandIndex][index1][index2] 
                    #else:
                    value = rasterBandVals[bandIndex][int(count/4)] #find in the list and match with color

                    rendererClasses = colorLayer.renderer().legendSymbologyItems()
                    for c in range(len(rendererClasses)-1):
                        if value >= float(rendererClasses[c][0]) and value <= float(rendererClasses[c+1][0]) :
                            rgb = rendererClasses[c][1].getRgb()
                            color =  (255<<24) + (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
                            break

                else:
                    if rendererType == "singlebandgray":
                        bandIndex = colorLayer.renderer().grayBand()-1
                    if rendererType == "hillshade":
                        bandIndex = colorLayer.renderer().band()-1
                    if rendererType == "contour":
                        try: bandIndex = colorLayer.renderer().inputBand()-1
                        except:
                            try: bandIndex = colorLayer.renderer().band()-1
                            except: bandIndex = 0
                    else: # e.g. single band data
                        bandIndex = 0
                    
                    if rasterBandVals[bandIndex][int(count/4)] >= rasterBandMinVal[bandIndex]: 
                        # REMAP band values to (0,255) range
                        valRange = (rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])
                        if valRange == 0: colorVal = 0
                        else: colorVal = int( (rasterBandVals[bandIndex][int(count/4)] - rasterBandMinVal[bandIndex]) / valRange * 255 )
                        color =  (255<<24) + (colorVal<<16) + (colorVal<<8) + colorVal

                colors.append([color,color,color,color])
                count += 4

            # after each row
            vertices_array.append(vertices)
            faces_array.append(faces)
            colors_array.append(colors)

            if v == 0: array_z.append(row_z)
            array_z.append(row_z_bottom)
        
        # after the entire loop
        faces_filtered = []
        colors_filtered = []
        vertices_filtered = []

        ## end of the the table
        smooth = False
        if terrain_transform is True or texture_transform is True:
            smooth = True
        if smooth is True and len(row_z)>2 and len(array_z)>2:
            array_z_nans = np.array(array_z)

            array_z_filled = np.array(array_z)
            mask = np.isnan(array_z_filled)
            array_z_filled[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), array_z_filled[~mask])

            sigma = 0.8 # for elevation
            if texture_transform is True:
                sigma = 1 # for texture

                # increase sigma if needed
                try:
                    unitsRaster = QgsUnitTypes.encodeUnit(selectedLayer.crs().mapUnits())
                    unitsElevation = QgsUnitTypes.encodeUnit(elevationLayer.crs().mapUnits())
                    print(unitsRaster)
                    print(unitsElevation)
                    resRasterX = get_scale_factor_to_meter(unitsRaster) * rasterResXY[0] 
                    resElevX = get_scale_factor_to_meter(unitsElevation) * elevationResX 
                    print(resRasterX)
                    print(resElevX)
                    if resRasterX/resElevX >=2 or resElevX/resRasterX >=2:
                        sigma = math.sqrt(max(resRasterX/resElevX, resElevX/resRasterX))
                        print(sigma)
                except: pass 

            gaussian_array = sp.ndimage.filters.gaussian_filter(array_z_filled, sigma, mode='nearest')

            for v in range(rasterDimensions[1] ): #each row, Y
                for h in range(rasterDimensions[0] ): #item in a row, X
                    if not np.isnan(array_z_nans[v][h]):

                        vertices_item = vertices_array[v][h]
                        #print(vertices_item)
                        vertices_item[2] = gaussian_array[v][h]
                        vertices_item[5] = gaussian_array[v+1][h]
                        vertices_item[8] = gaussian_array[v+1][h+1]
                        vertices_item[11] = gaussian_array[v][h+1]
                        vertices_filtered.extend(vertices_item) 
                        
                        currentFaces = len(faces_filtered)/5 *4
                        faces_filtered.extend([4, currentFaces,currentFaces+1,currentFaces+2,currentFaces+3])
                        #print(faces_filtered)
                        colors_filtered.extend(colors_array[v][h])
                        #print(colors_array[v][h])
        else:
            faces_filtered = np.array(faces_array).flatten().tolist()
            colors_filtered = np.array(colors_array).flatten().tolist()
            vertices_filtered = np.array(vertices_array).flatten().tolist()
        
        #if len(colors)/4*5 == len(faces) and len(colors)*3 == len(vertices):
        mesh = constructMeshFromRaster(vertices_filtered, faces_filtered, colors_filtered, dataStorage)
        if mesh is not None: 
            mesh.units = dataStorage.currentUnits
            b.displayValue = [ mesh ]
        else: 
            logToUser("Something went wrong. Mesh cannot be created, only raster data will be sent. ", level = 2, plugin = plugin.dockwidget)

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        
    return b


def featureToNative(feature: Base, fields: QgsFields, dataStorage = None):
    feat = QgsFeature()
    try:
        try: 
            speckle_geom = feature.geometry # for QGIS / ArcGIS Layer type from 2.14
        except:
            try: speckle_geom = feature["geometry"] # for QGIS / ArcGIS Layer type before 2.14
            except:  speckle_geom = feature # for created in other software

        if not isinstance(speckle_geom, list):
            qgsGeom = geometry.convertToNative(speckle_geom, dataStorage)
        
        elif isinstance(speckle_geom, list):
            if len(speckle_geom)==1:
                qgsGeom = geometry.convertToNative(speckle_geom[0], dataStorage)
            else: 
                qgsGeom = geometry.convertToNativeMulti(speckle_geom, dataStorage)

        if qgsGeom is not None: feat.setGeometry(qgsGeom)
        else: return None 

        feat.setFields(fields)  
        for field in fields:
            name = str(field.name())
            variant = field.type()
            #if name == "id": feat[name] = str(feature["applicationId"])

            try: 
                value = feature.attributes[name] # fro 2.14 onwards 
            except: 
                try: 
                    value = feature[name]
                except: 
                    if name == "Speckle_ID": 
                        try: 
                            value = str(feature["Speckle_ID"]) # if GIS already generated this field
                        except:
                            try: value = str(feature["speckle_id"]) 
                            except: value = str(feature["id"])
                    else: 
                        value = None 
                        #logger.logToUser(f"Field {name} not found", Qgis.Warning)
                        #return None
            
            if variant == QVariant.String: value = str(value) 
            
            if isinstance(value, str) and variant == QVariant.Date:  # 14
                y,m,d = value.split("(")[1].split(")")[0].split(",")[:3]
                value = QDate(int(y), int(m), int(d) ) 
            elif isinstance(value, str) and variant == QVariant.DateTime: 
                y,m,d,t1,t2 = value.split("(")[1].split(")")[0].split(",")[:5]
                value = QDateTime(int(y), int(m), int(d), int(t1), int(t2) )
            
            if variant == getVariantFromValue(value) and value != "NULL" and value != "None": 
                feat[name] = value
            
        return feat
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return feat

def cadFeatureToNative(feature: Base, fields: QgsFields, dataStorage = None):
    try:
        print("______________cadFeatureToNative")
        exist_feat = QgsFeature()
        try: speckle_geom = feature["geometry"] # for created in QGIS Layer type
        except:  speckle_geom = feature # for created in other software

        if isinstance(speckle_geom, list):
            qgsGeom = geometry.convertToNativeMulti(speckle_geom, dataStorage)
        else:
            qgsGeom = geometry.convertToNative(speckle_geom, dataStorage)

        if qgsGeom is not None: exist_feat.setGeometry(qgsGeom)
        else: return

        exist_feat.setFields(fields)  

        feat_updated = updateFeat(exist_feat, fields, feature)
        #print(fields.toList())
        #print(feature)
        #print(feat_updated)

        #### setting attributes to feature
        r'''
        for field in fields:
            #print(str(field.name()))
            name = str(field.name())
            variant = field.type()
            if name == "Speckle_ID": 
                value = str(feature["id"])
                feat[name] = value
            else: 
                # for values - normal or inside dictionaries: 
                try: value = feature[name]
                except:
                    rootName = name.split("_")[0]
                    newF, newVals = traverseDict({}, {}, rootName, feature[rootName][0])
                    for i, (k,v) in enumerate(newVals.items()):
                        if k == name: value = v; break
                # for all values: 
                if variant == QVariant.String: value = str(value) 
                
                
                if variant == getVariantFromValue(value) and value != "NULL" and value != "None": 
                    feat[name] = value
        '''       
        return feat_updated
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return 
    