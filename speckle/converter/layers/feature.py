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
from speckle.converter.geometry.mesh import constructMesh, constructMeshFromRaster
from speckle.converter.layers.Layer import RasterLayer
from speckle.logging import logger
from speckle.converter.layers.utils import getArrayIndicesFromXY, getVariantFromValue, getXYofArrayPoint, traverseDict, validateAttributeName 
from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)
import numpy as np 

from ui.logger import logToUser

def featureToSpeckle(fieldnames: List[str], f: QgsFeature, sourceCRS: QgsCoordinateReferenceSystem, targetCRS: QgsCoordinateReferenceSystem, project: QgsProject, selectedLayer: QgsVectorLayer or QgsRasterLayer, dataStorage = None):
    b = Base(units = dataStorage.currentUnits)
    try:
        #apply transformation if needed
        if sourceCRS != targetCRS:
            xform = QgsCoordinateTransform(sourceCRS, targetCRS, project)
            geometry = f.geometry()
            geometry.transform(xform)
            f.setGeometry(geometry)

        # Try to extract geometry
        try:
            geom = convertToSpeckle(f, selectedLayer, dataStorage)
            
            b["geometry"] = [] 
            if geom is not None and geom!="None": 
                if isinstance(geom, List):
                    for g in geom:
                        if g is not None and g!="None": 
                            b["geometry"].append(g)
                        else:
                            logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
                            print(g)
                else:
                    b["geometry"] = [geom]
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
            b[corrected] = f_name
        return b
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return b
          
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


def rasterFeatureToSpeckle(selectedLayer: QgsRasterLayer, projectCRS:QgsCoordinateReferenceSystem, project: QgsProject, dataStorage = None) -> Base:
    
    b = Base(units = dataStorage.currentUnits)
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
        rasterBandNoDataVal = []
        rasterBandMinVal = []
        rasterBandMaxVal = []
        rasterBandVals = []

        # Try to extract geometry
        reprojectedPt = QgsGeometry.fromPointXY(QgsPointXY())
        try:
            reprojectedPt = rasterOriginPoint
            if selectedLayer.crs()!= projectCRS: reprojectedPt = transform.transform(project, rasterOriginPoint, selectedLayer.crs(), projectCRS)
            pt = QgsGeometry.fromPointXY(reprojectedPt)
            geom = convertToSpeckle(pt, selectedLayer, dataStorage)
            if (geom != None):
                b['displayValue'] = [geom]
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

        b["X resolution"] = rasterResXY[0]
        b["Y resolution"] = rasterResXY[1]
        b["X pixels"] = rasterDimensions[0]
        b["Y pixels"] = rasterDimensions[1]
        b["X_min"] = reprojectedPt.x()
        b["Y_min"] = reprojectedPt.y() 
        b["Band count"] = rasterBandCount
        b["Band names"] = rasterBandNames
        b["NoDataVal"] = rasterBandNoDataVal
        # creating a mesh
        vertices = []
        faces = []
        colors = []
        count = 0
        rendererType = selectedLayer.renderer().type()
        #print(rendererType)
        # identify symbology type and if Multiband, which band is which color

        ############################################################# 
        terrain_transform = False
        texture_transform = False
        elevationLayer = None 
        textureLayer = None
        #height_list = rasterBandVals[0]
        height_array = None 
        if dataStorage.savedTransforms is not None:
            all_saved_transforms = [item.split("  ->  ")[1] for item in dataStorage.savedTransforms]
            all_saved_transform_layers = [item.split("  ->  ")[0] for item in dataStorage.savedTransforms]
            for item in dataStorage.savedTransforms:
                layer_name = item.split("  ->  ")[0]
                transform_name = item.split("  ->  ")[1]

                # identify existing elevation and texture layers 
                if "texture" in transform_name.lower():
                    # find a layer for texturing, if texture transformation exists 
                    for l in dataStorage.all_layers: 
                        if layer_name == l.name():

                            # also check if the layer is selected for sending
                            for sending_l in dataStorage.sending_layers:
                                if sending_l.name() == l.name():
                                    textureLayer = l 

                if "elevation" in transform_name.lower() and "mesh" in transform_name.lower() and "texture" not in transform_name.lower(): 
                    # find a layer for meshing, if mesh transformation exists 
                    for l in dataStorage.all_layers: 
                        if layer_name == l.name():
                            
                            # also check if the layer is selected for sending
                            for sending_l in dataStorage.sending_layers:
                                if sending_l.name() == l.name():
                                    elevationLayer = l 
                                    elevationSource = gdal.Open(l.source(), gdal.GA_ReadOnly)

                                    elevationX, elevationY = (elevationSource.GetGeoTransform()[0], elevationSource.GetGeoTransform()[3])
                                    elevationResX, elevationResY = (float(elevationSource.GetGeoTransform()[1]), float(elevationSource.GetGeoTransform()[5]))
                                    elevationWkt = elevationSource.GetProjection() 
                                    elevationBandCount = elevationLayer.bandCount()
                                    elevation_arrays = []
                                    elevation_mins = []
                                    elevation_maxs = []
                                    for txb in range(elevationBandCount):
                                        txb_band = elevationSource.GetRasterBand(txb+1)
                                        val_NA = txb_band.GetNoDataValue()
                                        
                                        array_band = txb_band.ReadAsArray()
                                        val_Average = np.nanmean(array_band)
                                        fakeArray = np.where( (array_band < const) | (array_band > -1*const) | (array_band == val_NA), val_Average, array_band)
                                        val_Min = np.nanmin(fakeArray)
                                        val_Max = np.nanmax(fakeArray)

                                        array_band = np.where( (array_band < const) | (array_band == val_NA), val_Min, array_band)
                                        
                                        elevation_arrays.append(array_band)
                                        elevation_mins.append(val_Min)
                                        elevation_maxs.append(val_Max)
                                    
                                    height_array = elevation_arrays[0]
                            
                # get any transformation for the current layer 
                if layer_name == selectedLayer.name():
                    print("Apply transform: " + transform_name)
                    if "elevation" in transform_name.lower() and "mesh" in transform_name.lower() and "texture" not in transform_name.lower():
                        terrain_transform = True 
                    elif "texture" in transform_name.lower() and elevationLayer is not None:
                        texture_transform = True 
                
        ############################################################
        z_vals_all = []
        xy_vals_all = []

        for v in range(rasterDimensions[1] ): #each row, Y
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
        
                #############################################################
                if terrain_transform is True and height_array is not None:
                    try: # top vertices
                        if v>=1 and h>=1: z1 = height_array[v-1][h-1]
                        else:
                            z_index = xy_vals_all.index((pt1.x(), pt1.y())) # value error if not found 
                            if z_index >=0: z1 = z_vals_all[z_index]
                            else: 1/0
                    except: 
                        z1 = height_array[v][h]
                    try:
                        if v>=1: z4 = height_array[v-1][h]
                        else: 1/0
                    except:
                        z4 = height_array[v][h]

                    try: # bottom vertices
                        z3 = height_array[v][h] # the only one advancing
                        if h>=1: z2 = height_array[v][h-1]
                        else: 1/0
                    except: 
                        z2 = height_array[v][h]
                    z_vals_all.extend([z1, z2, z3, z4])
                    xy_vals_all.extend([(pt1.x(), pt1.y()), (pt2.x(), pt2.y()), (pt3.x(), pt3.y()), (pt4.x(), pt4.y())])
                
                elif texture_transform is True and height_array is not None:
                    posX, posY = getXYofArrayPoint((rasterResXY[0], rasterResXY[1], originX, originY, rasterDimensions[1], rasterDimensions[0], rasterWkt), v, h, elevationWkt)
                    index1, index2 = getArrayIndicesFromXY((elevationResX, elevationResY, elevationX, elevationY, elevation_arrays[0].shape[0], elevation_arrays[0].shape[1], elevationWkt), posX, posY )
                    if index1 is None: 
                        count += 4
                        continue # skip the pixel
                    
                    # resolution might not match! Also pixels might be missing 
                    try: # top vertices
                        z_index = xy_vals_all.index((pt1.x(), pt1.y()))
                        if z_index >=0: z1 = z_vals_all[z_index]
                        else: 1/0
                    except: 
                        z1 = height_array[index1][index2]
                    try:
                        z_index = xy_vals_all.index((pt4.x(), pt4.y()))
                        if z_index >=0: z4 = z_vals_all[z_index]
                        else: 1/0
                    except:
                        z4 = height_array[index1][index2]

                    try: # bottom vertices
                        z3 = height_array[index1][index2] # the only one advancing
                        
                        z_index = xy_vals_all.index((pt2.x(), pt2.y()))
                        if z_index >=0: z2 = z_vals_all[z_index]
                        else: 1/0
                    except: 
                        z2 = height_array[index1][index2]
                    
                    z_vals_all.extend([z1, z2, z3, z4])
                    xy_vals_all.extend([(pt1.x(), pt1.y()), (pt2.x(), pt2.y()), (pt3.x(), pt3.y()), (pt4.x(), pt4.y())])

                ########################################################

                vertices.extend([pt1.x(), pt1.y(), z1, pt2.x(), pt2.y(), z2, pt3.x(), pt3.y(), z3, pt4.x(), pt4.y(), z4]) ## add 4 points
                current_vertices = len(faces) * 4 / 5
                faces.extend([4, current_vertices, current_vertices + 1, current_vertices + 2, current_vertices + 3])

                # color vertices according to QGIS renderer
                color = (0<<16) + (0<<8) + 0
                noValColor = selectedLayer.renderer().nodataColor().getRgb() 

                #if textureLayer is not None:
                #    colorLayer = textureLayer
                #    currentRasterBandCount = textureBandCount
                #else: 
                colorLayer = selectedLayer
                currentRasterBandCount = rasterBandCount

                if rendererType == "multibandcolor": 
                    valR = 0
                    valG = 0
                    valB = 0
                    bandRed = int(colorLayer.renderer().redBand())
                    bandGreen = int(colorLayer.renderer().greenBand())
                    bandBlue = int(colorLayer.renderer().blueBand())

                    for k in range(currentRasterBandCount): 
                        #if textureLayer is not None:
                        #    valRange = texture_maxs[k] - texture_mins[k] 
                        #    if valRange == 0: colorVal = 0
                        #    else: colorVal = int( (texture_arrays[k][index1][index2] - texture_mins[k] ) / valRange * 255 )
                        #else: 
                        valRange = (rasterBandMaxVal[k] - rasterBandMinVal[k])
                        if valRange == 0: colorVal = 0
                        else: colorVal = int( (rasterBandVals[k][int(count/4)] - rasterBandMinVal[k]) / valRange * 255 )
                            
                        if k+1 == bandRed: valR = colorVal
                        if k+1 == bandGreen: valG = colorVal
                        if k+1 == bandBlue: valB = colorVal

                    color =  (valR<<16) + (valG<<8) + valB 

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
                            color =  (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
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
                            color =  (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
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
                    
                    #if textureLayer is not None:
                    #    value = texture_arrays[bandIndex][index1][index2] 
                    #    valRange = texture_maxs[bandIndex] - texture_mins[bandIndex] 
                    #    if valRange == 0: colorVal = 0
                    #    else: colorVal = int( (texture_arrays[bandIndex][index1][index2] - texture_mins[bandIndex] ) / valRange * 255 )
                    #    color =  (colorVal<<16) + (colorVal<<8) + colorVal
                    #else: 
                    if rasterBandVals[bandIndex][int(count/4)] >= rasterBandMinVal[bandIndex]: 
                        # REMAP band values to (0,255) range
                        valRange = (rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])
                        if valRange == 0: colorVal = 0
                        else: colorVal = int( (rasterBandVals[bandIndex][int(count/4)] - rasterBandMinVal[bandIndex]) / valRange * 255 )
                        color =  (colorVal<<16) + (colorVal<<8) + colorVal

                colors.extend([color,color,color,color])
                count += 4

        mesh = constructMeshFromRaster(vertices, faces, colors, dataStorage)
        if b['displayValue'] is None:
            b['displayValue'] = []
        
        if terrain_transform is True and textureLayer is not None: # hide DEM elevation if texture layer will repeat the shape 
            b['displayValue'] = []
        elif terrain_transform is True or texture_transform is True: # don't included start pt for extruded terrain 
            b['displayValue'] = [ mesh ]
        else: 
            b['displayValue'] = [ mesh ]

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        
    return b


def featureToNative(feature: Base, fields: QgsFields, dataStorage = None):
    feat = QgsFeature()
    try:
        try: speckle_geom = feature["geometry"] # for created in QGIS / ArcGIS Layer type
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

            try: value = feature[name]
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
    