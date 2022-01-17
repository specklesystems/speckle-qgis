"""
Contains all Layer related classes and methods.
"""
import math
import os
from encodings.aliases import aliases
from typing import Any, List, Optional, Union

from osgeo import (  # # C:\Program Files\QGIS 3.20.2\apps\Python39\Lib\site-packages\osgeo
    gdal, osr)
from qgis.core import (Qgis, QgsCoordinateTransform, QgsGeometry, QgsMapLayer,
                       QgsPointXY, QgsRasterBandStats, QgsRasterLayer,
                       QgsVectorLayer, QgsWkbTypes, QgsProject, QgsLayerTree, QgsLayerTreeNode, QgsFeature, QgsField, QgsCoordinateReferenceSystem)
from qgis.gui import QgsRendererWidget
from qgis.PyQt.QtCore import QVariant
from speckle.converter.geometry import (convertToNative, convertToSpeckle,
                                        transform)
from speckle.converter.geometry.mesh import rasterToMesh
from speckle.logging import logger
from specklepy.objects import Base

#import numpy as np


class CRS(Base):
    """A very basic GIS Coordinate Reference System stored in wkt format"""
    name: str
    wkt: str
    units: str

    def __init__(self, name: str, wkt: str, units: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.wkt = wkt
        self.units = units

class Layer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name=None,
        crs=None,
        features: List[Base] = [],
        layerType: str = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.type = layerType
        self.features = features


def getLayers(tree: QgsLayerTree, parent: QgsLayerTreeNode) -> List[QgsLayerTreeNode]:
    """Gets a list of all layers in the given QgsLayerTree"""

    children = parent.children()
    layers = []
    for node in children:
        if tree.isLayer(node):
            layers.append(node)
            continue
        if tree.isGroup(node):
            layers.extend(getLayers(tree, node))
    return layers


def convertSelectedLayers(layers, selectedLayerNames, projectCRS, project):
    """Converts the current selected layers to Speckle"""
    result = []
    for layer in layers:
        if layer.name() in selectedLayerNames:
            result.append(layerToSpeckle(layer, projectCRS, project))
    return result


'''
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
'''    

def layerToSpeckle(layer, projectCRS, project): #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    layerName = layer.name()
    selectedLayer = layer.layer()
    crs = selectedLayer.crs()
    units = "m"
    if crs.isGeographic(): units = "m" ## specklepy.logging.exceptions.SpeckleException: SpeckleException: Could not understand what unit degrees is referring to. Please enter a valid unit (eg ['mm', 'cm', 'm', 'in', 'ft', 'yd', 'mi']). 
    layerObjs = []
    # Convert CRS to speckle, use the projectCRS
    speckleCrs = CRS(name=crs.authid(), wkt=crs.toWkt(), units=units) 
    speckleReprojectedCrs = CRS(name=projectCRS.authid(), wkt=projectCRS.toWkt(), units=units) 

    if isinstance(selectedLayer, QgsVectorLayer):

        fieldnames = [field.name() for field in selectedLayer.fields()]

        # write feature attributes
        for f in selectedLayer.getFeatures():
            b = featureToSpeckle(fieldnames, f, crs, projectCRS, project)
            layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleReprojectedCrs, layerObjs)
        layerBase.applicationId = selectedLayer.id()
        return layerBase

    if isinstance(selectedLayer, QgsRasterLayer):
        # write feature attributes
        b = rasterFeatureToSpeckle(selectedLayer, projectCRS, project)
        layerObjs.append(b)
        # Convert layer to speckle
        layerBase = Layer(layerName, speckleReprojectedCrs, layerObjs)
        layerBase.applicationId = selectedLayer.id()
        return layerBase

def featureToSpeckle(fieldnames, f, sourceCRS, targetCRS, project):
    b = Base()

    #apply transformation if needed
    if sourceCRS != targetCRS:
        xform = QgsCoordinateTransform(sourceCRS, targetCRS, project)
        geometry = f.geometry()
        geometry.transform(xform)
        f.setGeometry(geometry)

    # Try to extract geometry
    try:
        geom = convertToSpeckle(f)
        if geom is not None:
            b["displayValue"] = geom
    except Exception as error:
        logger.logToUser("Error converting geometry: " + str(error), Qgis.Critical)

    for name in fieldnames:
        corrected = name.replace("/", "_").replace(".", "-")
        if corrected == "id":
            corrected == "applicationId"
        b[corrected] = str(f[name])
    return b

def rasterFeatureToSpeckle(selectedLayer, projectCRS, project):
    rasterBandCount = selectedLayer.bandCount()
    rasterBandNames = []
    rasterDimensions = [selectedLayer.width(), selectedLayer.height()]
    #if rasterDimensions[0]*rasterDimensions[1] > 1000000 :
    #    logger.logToUser("Large layer: ", Qgis.Warning)

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
        if selectedLayer.crs()!= projectCRS: reprojectedPt = transform.transform(rasterOriginPoint, selectedLayer.crs(), projectCRS)
        pt = QgsGeometry.fromPointXY(reprojectedPt)
        geom = convertToSpeckle(pt)
        if (geom != None):
            b['displayValue'] = [geom]
    except Exception as error:
        logger.logToUser("Error converting point geometry: " + str(error), Qgis.Critical)

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
        b["@(10000)" + selectedLayer.bandName(index+1) + "_values"] = bandValsFlat #[0:int(max_values/rasterBandCount)]
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
                pt1 = transform.transform(src = pt1, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
                pt2 = transform.transform(src = pt2, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
                pt3 = transform.transform(src = pt3, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
                pt4 = transform.transform(src = pt4, crsSrc = selectedLayer.crs(), crsDest = projectCRS)
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

    '''# testing, only for receiving layers
    source_folder = selectedLayer.source().replace(selectedLayer.source().split('/')[len(selectedLayer.source().split('/'))-1],"")
    epsg = int(str(projectCRS).split(":")[len(str(projectCRS).split(":"))-1].split(">")[0])
    receiveRaster(project, source_folder, selectedLayer.name(), epsg, rasterDimensions,  rasterBandCount, rasterBandVals, reprojectedPt, rasterResXY)
    '''
    return b

'''
class fakeNpArray(object):
    def __init__(self, shape=None):
        self.shape=shape
	
### WORKING: Creating raster layer from the data. ISSUES: import numpy, save to local folder
def receiveRaster(project, source_folder, name, epsg, rasterDimensions, bands, rasterBandVals, pt, rasterResXY): 
    ## https://opensourceoptions.com/blog/pyqgis-create-raster/
    # creating file in temporary folder: https://stackoverflow.com/questions/56038742/creating-in-memory-qgsrasterlayer-from-the-rasterization-of-a-qgsvectorlayer-wit
    fn = source_folder + name + '_received_raster.tif'
    print(fn)
    
    driver = gdal.GetDriverByName('GTiff')
    # create raster dataset
    ds = driver.Create(fn, xsize=rasterDimensions[0], ysize=rasterDimensions[1], bands=bands, eType=gdal.GDT_Float32)

    # Write data to raster band
    for i in range(bands):
        #rasterband = np.zeros((10,10))
        rasterband = np.array(rasterBandVals[i])
        rasterband = np.reshape(rasterband,(rasterDimensions[1], rasterDimensions[0]))
        rasterband = []
        for k in range(rasterDimensions[0]):
            row = []
            for n in range(rasterDimensions[1]):
                row.append(rasterBandVals[i][n+n*k])
            rasterband.append(row)
        print(rasterband)
        #rasterband.shape = (rasterDimensions[1], rasterDimensions[0])
        ds.GetRasterBand(i+1).WriteArray(rasterband) # or "rasterband.T"

    # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
    ds.SetGeoTransform([pt.x(), rasterResXY[0], 0, pt.y(), 0, rasterResXY[1]])
    # create a spatial reference object
    srs = osr.SpatialReference()
    #  For the Universal Transverse Mercator the SetUTM(Zone, North=1 or South=2)
    # Other methods can set the spatial reference from well-known text or EPSG code
    #srs.SetUTM(12,1) 
    #srs.SetWellKnownGeogCS('NAD83')
    srs.ImportFromEPSG(epsg) # from https://gis.stackexchange.com/questions/34082/creating-raster-layer-from-numpy-array-using-pyqgis
    ds.SetProjection(srs.ExportToWkt())
    # close the rater datasource by setting it equal to None
    ds = None
    #add the new raster to the QGIS interface
    #rlayer = iface.addRasterLayer(fn)
    raster_layer = QgsRasterLayer(fn, 'Layer_name', 'gdal')
    project.addMapLayer(raster_layer)
'''

class RasterLayer(Base, speckle_type="Objects.Geometry." + "RasterLayer", chunkable={"Raster": 1000}, detachable={"Raster"}):
    Raster: Optional[List[str]] = None

    @ classmethod
    def from_list(cls, args: List[Any]) -> "RasterLayer":
        return cls(
            Raster=args,
        )

    def to_list(self) -> List[Any]:
        if(self.Raster is None):
            raise Exception("This RasterLayer has no data set.")
        return self.Raster


def featureToNative(feature: Base):
    return None


def layerToNative(layer: Layer) -> Union[QgsVectorLayer, QgsRasterLayer, None]:
    layerType = type(layer.type)
    if layer.type is None:
        # Handle this case
        return
    elif layer.type.endswith("VectorLayer"):
        vectorLayerToNative(layer)
    elif layer.type.endswith("RasterLayer"):
        rasterLayerToNative(layer)
    return None


def getLayerAttributes(layer: Layer):
    names = {}
    for feature in layer.features:
        featNames = feature.get_member_names()
        for n in featNames:
            if not (n in names):
                try:
                    value = feature[n]
                    variant = getVariantFromValue(value)
                    if variant:
                        names[n] = QgsField(n, variant)
                except Exception as error:
                    logger.log(str(error))
    return names.values()

def getVariantFromValue(value):
    pairs = {
        str: QVariant.String,
        float: QVariant.Double,
        int: QVariant.Int,
        bool: QVariant.Bool,
    }
    t = type(value)
    return pairs[t]

def vectorLayerToNative(layer: Layer):
    opts = QgsVectorLayer.LayerOptions()
    vl = None
    for lyr in QgsProject.instance().mapLayers().values():
        if lyr.id() == layer.applicationId:
            vl = lyr
            break
    if vl is None:
        vl = QgsVectorLayer("Speckle", layer.name, "memory", opts)
        pr = vl.dataProvider()
        vl.startEditing()
        attrs = getLayerAttributes(layer)
        pr.addAttributes(attrs)
        vl.setCrs(QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt))
        vl.commitChanges()
    vl.startEditing()
    # fets = [featureToNative(feature) for feature in layer.features]
    # vl.addFeatures(fets)
    vl.commitChanges()
    QgsProject.instance().addMapLayer(vl)
    return None

def rasterLayerToNative(layer: Layer):
    rl = QgsRasterLayer("Speckle", layer.name, "memory", QgsRasterLayer.LayerOptions())

    return None

def get_type(type_name):
    try:
        return getattr(__builtins__, type_name)
    except AttributeError:
        try:
            obj = globals()[type_name]
        except KeyError:
            return None
        return repr(obj) if isinstance(obj, type) else None
