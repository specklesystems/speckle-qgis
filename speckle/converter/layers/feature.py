from distutils.log import error
import inspect
import math
from tokenize import String
from typing import List
from qgis._core import QgsCoordinateTransform, Qgis, QgsPointXY, QgsGeometry, QgsRasterBandStats, QgsFeature, QgsFields, \
    QgsField, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem, QgsProject
from specklepy.objects import Base

from typing import Dict, Any

from PyQt5.QtCore import QVariant, QDate, QDateTime
from speckle.converter import geometry
from speckle.converter.geometry import convertToSpeckle, transform
from speckle.converter.geometry.mesh import constructMesh, constructMeshFromRaster
from speckle.converter.layers.Layer import RasterLayer
from speckle.logging import logger
from speckle.converter.layers.utils import getVariantFromValue, traverseDict, validateAttributeName 
from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)

from ui.logger import logToUser

def featureToSpeckle(fieldnames: List[str], f: QgsFeature, sourceCRS: QgsCoordinateReferenceSystem, targetCRS: QgsCoordinateReferenceSystem, project: QgsProject, selectedLayer: QgsVectorLayer or QgsRasterLayer, dataStorage = None):
    b = Base(units = "m")
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
          
def bimFeatureToNative(exist_feat: QgsFeature, feature: Base, fields: QgsFields, crs, path: str):
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
    
    b = Base(units = "m")
    try:
        rasterBandCount = selectedLayer.bandCount()
        rasterBandNames = []
        rasterDimensions = [selectedLayer.width(), selectedLayer.height()]
        #if rasterDimensions[0]*rasterDimensions[1] > 1000000 :
        #   logToUser("Large layer: ", level = 1, func = inspect.stack()[0][3])

        ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
        rasterOriginPoint = QgsPointXY(ds.GetGeoTransform()[0], ds.GetGeoTransform()[3])
        rasterResXY = [float(ds.GetGeoTransform()[1]), float(ds.GetGeoTransform()[5])]
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
                if dataStorage.savedTransforms is not None:
                    for item in dataStorage.savedTransforms:
                        layer_name = item.split("  ->  ")[0]
                        transform_name = item.split("  ->  ")[1]
                        if layer_name == selectedLayer.name():
                            print("Apply transform: " + transform_name)
                            if "elevation to mesh" in transform_name.lower():

                                height_list = rasterBandVals[0]
                                try: # top vertices
                                    z1 = height_list[int( count/4 ) - rasterDimensions[0] -1 ]
                                except: 
                                    z1 = height_list[int( count/4 )]
                                try:
                                    z4 = height_list[int( count/4 ) - rasterDimensions[0] ]
                                except:
                                    z4 = height_list[int( count/4 )]

                                try: # bottom vertices
                                    z3 = height_list[int( count/4 )] # the only one advancing
                                    z2 = height_list[int( count/4 ) -1 ]
                                except: 
                                    z2 = height_list[int( count/4 )]

                ########################################################

                vertices.extend([pt1.x(), pt1.y(), z1, pt2.x(), pt2.y(), z2, pt3.x(), pt3.y(), z3, pt4.x(), pt4.y(), z4]) ## add 4 points
                faces.extend([4, count, count+1, count+2, count+3])

                # color vertices according to QGIS renderer
                color = (0<<16) + (0<<8) + 0
                noValColor = selectedLayer.renderer().nodataColor().getRgb()

                if rendererType == "multibandcolor":
                    redBand = int(selectedLayer.renderer().redBand())
                    greenBand = int(selectedLayer.renderer().greenBand())
                    blueBand = int(selectedLayer.renderer().blueBand())
                    rVal = 0
                    gVal = 0
                    bVal = 0
                    for k in range(rasterBandCount):
                        if rasterBandVals[k][int(count/4)] >= rasterBandMinVal[k]: 
                            #### REMAP band values to (0,255) range
                            valRange = (rasterBandMaxVal[k] - rasterBandMinVal[k])
                            if valRange == 0: 
                                if rasterBandMinVal[k] ==0: colorVal = 0
                                else: colorVal = 255
                            else: colorVal = int( (rasterBandVals[k][int(count/4)] - rasterBandMinVal[k]) / valRange * 255 )
                            
                            if k+1 == redBand: rVal = colorVal
                            if k+1 == greenBand: gVal = colorVal
                            if k+1 == blueBand: bVal = colorVal
                    color =  (rVal<<16) + (gVal<<8) + bVal
                    # for missing values (check by 1st band)
                    if rasterBandVals[0][int(count/4)] != rasterBandVals[0][int(count/4)]:
                        color = (noValColor[0]<<16) + (noValColor[1]<<8) + noValColor[2]

                elif rendererType == "paletted":
                    bandIndex = selectedLayer.renderer().band()-1 #int
                    value = rasterBandVals[bandIndex][int(count/4)] #find in the list and match with color

                    rendererClasses = selectedLayer.renderer().classes()
                    for c in range(len(rendererClasses)-1):
                        if value >= rendererClasses[c].value and value <= rendererClasses[c+1].value :
                            rgb = rendererClasses[c].color.getRgb()
                            color =  (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
                            break

                elif rendererType == "singlebandpseudocolor":
                    bandIndex = selectedLayer.renderer().band()-1 #int
                    value = rasterBandVals[bandIndex][int(count/4)] #find in the list and match with color

                    rendererClasses = selectedLayer.renderer().legendSymbologyItems()
                    for c in range(len(rendererClasses)-1):
                        if value >= float(rendererClasses[c][0]) and value <= float(rendererClasses[c+1][0]) :
                            rgb = rendererClasses[c][1].getRgb()
                            color =  (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
                            break

                else:
                    if rendererType == "singlebandgray":
                        bandIndex = selectedLayer.renderer().grayBand()-1
                    if rendererType == "hillshade":
                        bandIndex = selectedLayer.renderer().band()-1
                    if rendererType == "contour":
                        try: bandIndex = selectedLayer.renderer().inputBand()-1
                        except:
                            try: bandIndex = selectedLayer.renderer().band()-1
                            except: bandIndex = 0
                    else: # e.g. single band data
                        bandIndex = 0
                    
                    if rasterBandVals[bandIndex][int(count/4)] >= rasterBandMinVal[bandIndex]: 
                        # REMAP band values to (0,255) range
                        valRange = (rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])
                        if valRange == 0: 
                            if rasterBandMinVal[bandIndex] ==0: colorVal = 0
                            else: colorVal = 255
                        else: colorVal = int( (rasterBandVals[bandIndex][int(count/4)] - rasterBandMinVal[bandIndex]) / valRange * 255 )
                        color =  (colorVal<<16) + (colorVal<<8) + colorVal

                colors.extend([color,color,color,color])
                count += 4

        mesh = constructMeshFromRaster(vertices, faces, colors)
        if(b['displayValue'] is None):
            b['displayValue'] = []
        b['displayValue'].append(mesh)
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        
    return b


def featureToNative(feature: Base, fields: QgsFields):
    feat = QgsFeature()
    try:
        try: speckle_geom = feature["geometry"] # for created in QGIS / ArcGIS Layer type
        except:  speckle_geom = feature # for created in other software

        if isinstance(speckle_geom, list):
            qgsGeom = geometry.convertToNativeMulti(speckle_geom)
        else:
            qgsGeom = geometry.convertToNative(speckle_geom)

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

def cadFeatureToNative(feature: Base, fields: QgsFields):
    try:
        print("______________cadFeatureToNative")
        exist_feat = QgsFeature()
        try: speckle_geom = feature["geometry"] # for created in QGIS Layer type
        except:  speckle_geom = feature # for created in other software

        if isinstance(speckle_geom, list):
            qgsGeom = geometry.convertToNativeMulti(speckle_geom)
        else:
            qgsGeom = geometry.convertToNative(speckle_geom)

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
    