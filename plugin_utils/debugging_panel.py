
r'''
layer = QgsVectorLayer('CompoundCurve?crs=epsg:4326', 'polygon' , 'memory')
prov = layer.dataProvider()
feat = QgsFeature()
c = QgsCompoundCurve()
c.addCurve(QgsCircularString(QgsPoint(-2,0,0),QgsPoint(-2,-2,0),QgsPoint(-4,-1,0)))
feat.setGeometry(c)
prov.addFeatures([feat])
QgsProject.instance().addMapLayer(layer, True)
'''
#### get layers 
project = QgsProject.instance()
projectCRS = project.crs()
layerTreeRoot = project.layerTreeRoot()

def getLayers(tree: QgsLayerTree, parent: QgsLayerTreeNode):
    children = parent.children()
    layers = []
    for node in children:
        if tree.isLayer(node):
            if isinstance(node.layer(), QgsVectorLayer) or isinstance(node.layer(), QgsRasterLayer): layers.append(node)
            continue
        if tree.isGroup(node):
            for lyr in getLayers(tree, node):
                if isinstance(lyr.layer(), QgsVectorLayer) or isinstance(lyr.layer(), QgsRasterLayer): layers.append(lyr) 
            #layers.extend( [ lyr for lyr in getLayers(tree, node) if isinstance(lyr.layer(), QgsVectorLayer) or isinstance(lyr.layer(), QgsRasterLayer) ] )
    return layers

layers = getLayers(layerTreeRoot, layerTreeRoot)
print(layers)
layer = layers[0].layer()

#layers[0].layer().loadNamedStyle(r'renderer3d.qml')

######################################## rasters ################################
raster_layer = layers[5].layer()

dataProvider = raster_layer.dataProvider()

########### singleband
band = 1
contrast = QgsContrastEnhancement()
contrast.setContrastEnhancementAlgorithm(1)
contrast.setMaximumValue(100)
contrast.setMinimumValue(0)

rendererNew = QgsSingleBandGrayRenderer(dataProvider, int(band))
rendererNew.setContrastEnhancement(contrast)

############ multiband 
redBand = 1
greenBand = 2
blueBand = 3
rendererNew = QgsMultiBandColorRenderer(dataProvider,int(redBand),int(greenBand),int(blueBand))

contrastR = QgsContrastEnhancement()
contrastR.setContrastEnhancementAlgorithm(1)
contrastR.setMaximumValue(10000)
contrastR.setMinimumValue(0)
#rendererNew.setRedContrastEnhancement(contrastR)

rendererNew.minMaxOrigin().setLimits(QgsRasterMinMaxOrigin.Limits(1))

raster_layer.setRenderer(rendererNew)

################# triangulation

def getPolyBoundary(geom):
    vertices = []
    segmList = []
    try: 
        extRing = geom.exteriorRing()
        pt_iterator = extRing.vertices()
    except: 
        try:  
            extRing = geom.constGet().exteriorRing()
            pt_iterator = geom.vertices()
        except: 
            extRing = geom
            pt_iterator = geom.vertices()
    
    pointListLocal = []
    startLen = len(vertices)
    for pt in enumerate(pt_iterator): pointListLocal.append(pt)
    for i,pt in enumerate(pointListLocal):
        #print(pt)
        vertices.append([pt[1].x(),pt[1].y()])
        if i>0: 
            segmList.append([startLen+i-1, startLen+i])
        if i == len(pointListLocal)-1: #also add a cap
            segmList.append([startLen+i, startLen])
    ########### get voids
    
    try:
        for i in range(geom.numInteriorRings()):
            intRing = geom.interiorRing(i)
            pt_iterator = geom.vertices()

            pointListLocal = []
            startLen = len(vertices)
            for pt in pt_iterator: pointListLocal.append(pt) 
            for i,pt in enumerate(pointListLocal):
                vertices.append([pt[1].x(),pt[1].y()])
                if i>0: 
                    segmList.append([startLen+i-1, startLen+i])
                if i == len(pointListLocal)-1: #also add a cap
                    segmList.append([startLen+i, startLen])
    except: 
        try:
            geom = geom.constGet()
            for i in range(geom.numInteriorRings()):
                intRing = geom.interiorRing(i)
                pt_iterator = geom.vertices()

                pointListLocal = []
                startLen = len(vertices)
                for pt in pt_iterator: pointListLocal.append(pt) 
                for i,pt in enumerate(pointListLocal):
                    vertices.append([pt[1].x(),pt[1].y()])
                    if i>0: 
                        segmList.append([startLen+i-1, startLen+i])
                    if i == len(pointListLocal)-1: #also add a cap
                        segmList.append([startLen+i, startLen])
        except: pass     
    return vertices, segmList


############################ 

import triangle as tr

shapes = [f.geometry() for f in layer.getFeatures()]
all_polygons = []
for sh in shapes:
    vertices = []
    segments = []
    holes = []
    vertices, segments = getPolyBoundary(sh)
    print(vertices)
    print(segments)
    dict_shape= {'vertices': vertices, 'segments': segments}
    t = tr.triangulate(dict_shape, 'p')
    all_polygons.append(t)

print(all_polygons)


########### create Vector layer

project = QgsProject.instance()
newName = "new layer"
authid = "EPSG:3857" #4326
geomType = "Polygon"

vl = QgsVectorLayer(geomType+ "?crs=" + authid, newName, "memory")
#vl.setCrs(crs)
project.addMapLayer(vl, True)

pr = vl.dataProvider()
vl.startEditing()

fets = []
for i in range(5):
    feat = QgsFeature()
    qgsGeom = QgsPolygon()
    pt_list = [QgsPoint(0,0,0), QgsPoint(5,7,0), QgsPoint(1,4,0)]
    polyline = QgsLineString(pt_list)
    qgsGeom.setExteriorRing(polyline)
    #qgsGeom.addInteriorRing(QgsLineString())
    feat.setGeometry(qgsGeom)
    fets.append(feat) 


r'''
newFields = QgsFields()
for f in layer.features: 
    new_feat = featureToNative(f, newFields)
    if new_feat is not None and new_feat != "": fets.append(new_feat)
    else:
        logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
# add Layer attribute fields
pr.addAttributes(newFields.toList())
vl.updateFields()
'''

pr.addFeatures(fets)
vl.updateExtents()
vl.commitChanges()


