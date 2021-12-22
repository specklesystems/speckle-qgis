import os
import math
from qgis.core import Qgis, QgsWkbTypes, QgsPointXY, QgsGeometry, QgsMapLayer, QgsRasterBandStats, QgsRasterLayer, QgsVectorLayer, QgsCoordinateTransform
from speckle.logging import logger
from qgis.gui import QgsRendererWidget
from speckle.converter.geometry import extractGeometry, rasterToMesh, transform
from typing import Any, List

from encodings.aliases import aliases
from osgeo import gdal ## C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo

from specklepy.objects import Base

class CRS(Base):
    name: str
    wkt: str
    units: str

    def __init__(self, name, wkt, units, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.wkt = wkt
        self.units = units

class Layer(Base, chunkable={"features": 100}):
    def __init__(self, name, crs, features=[], **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.features = features


def getLayers(tree, parent):
    children = parent.children()
    layers = []
    for node in children:
        isLayer = tree.isLayer(node)
        if isLayer:
            layers.append(node)
            continue
        isGroup = tree.isGroup(node)
        if isGroup:
            layers.extend(getLayers(tree, node))
    return layers


def convertSelectedLayers(layers, selectedLayerNames, projectCRS, project):
    result = []
    for layer in layers:
        # if not(hasattr(layer, "fields")):
        #     continue
        if layer.name() in selectedLayerNames:
            if layer.layer().crs() == projectCRS:
                reprojectedLayer = layer.layer() 
            else: 
                reprojectedLayer = reprojectLayer(layer, projectCRS, project)
            result.append(layerToSpeckle(reprojectedLayer, projectCRS))
    return result

def reprojectLayer(layer, targetCRS, project):

    if isinstance(layer.layer(), QgsVectorLayer):
        ### create copy of the layer in memory
        typeGeom = QgsWkbTypes.displayString(int(layer.layer().wkbType())) #returns e.g. Point, Polygon, Line
        crsId = layer.layer().crs().authid()
        layerReprojected = QgsVectorLayer(typeGeom+"?crs="+crsId, layer.name() + "_copy", "memory")
        
        ### copy fields/attributes to the new layer
        fields = layer.layer().dataProvider().fields().toList()
        layerReprojected.dataProvider().addAttributes(fields)
        layerReprojected.updateFields()

        ### get and transform the features
        features=[f for f in layer.layer().getFeatures()]
        xform = QgsCoordinateTransform(layer.layer().crs(), targetCRS, project)
        for feature in features:
            geometry = feature.geometry()
            geometry.transform(xform)
            feature.setGeometry(geometry)

        layerReprojected.dataProvider().addFeatures(features)
        layerReprojected.setCrs(targetCRS)

        return layerReprojected
    
    else:
        return layer.layer()
    

def layerToSpeckle(layer, projectCRS): #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    layerName = layer.name()
    selectedLayer = layer #.layer()
    crs = selectedLayer.crs()
    units = "m"
    if crs.isGeographic(): units = "degrees"
    layerObjs = []
    # Convert CRS to speckle
    speckleCrs = CRS(name=crs.authid(), wkt=crs.toWkt(), units=units)

    if isinstance(selectedLayer, QgsVectorLayer):

        fieldnames = [field.name() for field in selectedLayer.fields()]

        # write feature attributes
        for f in selectedLayer.getFeatures():
            b = featureToSpeckle(fieldnames, f)
            layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleCrs, layerObjs)
        layerBase.applicationId = selectedLayer.id()
        return layerBase

    if isinstance(selectedLayer, QgsRasterLayer):
        
        # write feature attributes
        b = rasterFeatureToSpeckle(selectedLayer, projectCRS)
        layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleCrs, layerObjs)
        layerBase.applicationId = selectedLayer.id()
        return layerBase

def featureToSpeckle(fieldnames, f):
    b = Base()
    # Try to extract geometry
    try:
        geom = extractGeometry(f)
        if (geom != None):
            b['displayValue'] = geom
    except Exception as error:
        logger.logToUser("Error converting geometry: " + error, Qgis.Critical)

    for name in fieldnames:
        corrected = name.replace("/", "_").replace(".", "-")
        if(corrected == "id"):
            corrected == "applicationId"
        b[corrected] = str(f[name])
    return b

def rasterFeatureToSpeckle(selectedLayer, projectCRS):
    rasterBandCount = selectedLayer.bandCount()
    rasterBandNames = []
    rasterDimensions = [selectedLayer.width(), selectedLayer.height()]

    ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
    rasterOriginPoint = QgsPointXY(ds.GetGeoTransform()[0], ds.GetGeoTransform()[3])
    rasterResXY = [ds.GetGeoTransform()[1],ds.GetGeoTransform()[5]]
    rasterBandNoDataVal = []
    rasterBandMinVal = []
    rasterBandMaxVal = []
    rasterBandVals = []

    b = Base()
    # Try to extract geometry
    try:
        reprojectedPt = rasterOriginPoint
        if selectedLayer.crs()!= projectCRS: reprojectedPt = transform(rasterOriginPoint, selectedLayer.crs(), projectCRS)
        pt = QgsGeometry.fromPointXY(reprojectedPt)
        geom = extractGeometry(pt)
        if (geom != None):
            b['displayValue'] = [geom]
    except Exception as error:
        logger.logToUser("Error converting geometry: " + error, Qgis.Critical)

    for index in range(rasterBandCount):
        rasterBandNames.append(selectedLayer.bandName(index+1))
        rb = ds.GetRasterBand(index+1)
        valMin = selectedLayer.dataProvider().bandStatistics(index+1, QgsRasterBandStats.All).minimumValue
        valMax = selectedLayer.dataProvider().bandStatistics(index+1, QgsRasterBandStats.All).maximumValue
        bandVals = rb.ReadAsArray().tolist()

        '''
        ## reduce resolution if needed: 
        if totalValues>max_values : 
            bandVals_resized = [] #list of lists
            factor = 1 #recalculate factor to reach max size
            for i in range(1,20):
                if totalValues/(i*i) <= max_values:
                    factor = i
                    break
            for item in bandVals: #reduce each row and each column
                bandVals_resized = [bandVals]
        '''
        bandValsFlat = []
        [bandValsFlat.extend(item) for item in bandVals]
        #look at mesh chunking 
        b["@(10000)" + selectedLayer.bandName(index+1) + str(index+1) + " values"] = bandValsFlat #[0:int(max_values/rasterBandCount)]
        rasterBandVals.append(bandValsFlat)
        rasterBandNoDataVal.append(rb.GetNoDataValue())
        rasterBandMinVal.append(valMin)
        rasterBandMaxVal.append(valMax)

    b["X resolution"] = rasterResXY[0]
    b["Y resolution"] = rasterResXY[1]
    b["X pixels"] = rasterDimensions[0]
    b["Y pixels"] = rasterDimensions[1]
    b["Band count"] = rasterBandCount
    b["Band names"] = rasterBandNames

    # creating a mesh
    vertices = []
    faces = []
    colors = []
    count = 0
    rendererType = selectedLayer.renderer().type()
    print(rendererType)
    # TODO identify symbology type and if Multiband, which band is which color
    for v in range(rasterDimensions[1] ): #each row, Y
        for h in range(rasterDimensions[0] ): #item in a row, X
            pt1 = QgsPointXY(rasterOriginPoint.x()+h*rasterResXY[0], rasterOriginPoint.y()+v*rasterResXY[1])
            pt2 = QgsPointXY(rasterOriginPoint.x()+h*rasterResXY[0], rasterOriginPoint.y()+(v+1)*rasterResXY[1])
            pt3 = QgsPointXY(rasterOriginPoint.x()+(h+1)*rasterResXY[0], rasterOriginPoint.y()+(v+1)*rasterResXY[1])
            pt4 = QgsPointXY(rasterOriginPoint.x()+(h+1)*rasterResXY[0], rasterOriginPoint.y()+v*rasterResXY[1])
            # first, get point coordinates with correct position and resolution, then reproject each: 
            if selectedLayer.crs()!= projectCRS: 
                pt1 = transform(src = pt1, crs_src = selectedLayer.crs(), crsDest = projectCRS)
                pt2 = transform(src = pt2, crs_src = selectedLayer.crs(), crsDest = projectCRS)
                pt3 = transform(src = pt3, crs_src = selectedLayer.crs(), crsDest = projectCRS)
                pt4 = transform(src = pt4, crs_src = selectedLayer.crs(), crsDest = projectCRS)
            vertices.extend([pt1.x(), pt1.y(), 0, pt2.x(), pt2.y(), 0, pt3.x(), pt3.y(), 0, pt4.x(), pt4.y(), 0]) ## add 4 points
            faces.extend([4, count, count+1, count+2, count+3])

            # color vertices according to QGIS renderer
            color = (0<<16) + (0<<8) + 0
            noValColor = selectedLayer.renderer().nodataColor().getRgb()
            
            if rendererType == "multibandcolor":
                redBand = selectedLayer.renderer().redBand()
                greenBand = selectedLayer.renderer().greenBand()
                blueBand = selectedLayer.renderer().blueBand()
                rVal = 0
                gVal = 0
                bVal = 0
                for k in range(rasterBandCount): 
                    #### REMAP band values to (0,255) range
                    valRange = (rasterBandMaxVal[k] - rasterBandMinVal[k])
                    colorVal = int( (rasterBandVals[k][int(count/4)] - rasterBandMinVal[k]) / valRange * 255 )
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
                # REMAP band values to (0,255) range
                valRange = (rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])
                colorVal = int( (rasterBandVals[bandIndex][int(count/4)] - rasterBandMinVal[bandIndex]) / valRange * 255 )
                color =  (colorVal<<16) + (colorVal<<8) + colorVal

            colors.extend([color,color,color,color])
            count += 4
    
    mesh = rasterToMesh(vertices, faces, colors)
    b['displayValue'].append(mesh)
    
    return b

class RasterLayer(Base, speckle_type="Objects.Geometry." + "RasterLayer", chunkable={"Raster": 1000}, detachable={"Raster"}):
    Raster: List[str] = None

    @ classmethod
    def from_list(cls, args: List[Any]) -> "RasterLayer":
        return cls(
            Raster=args,
        )

    def to_list(self) -> List[Any]:
        return self.Raster
