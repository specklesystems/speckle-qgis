

import os; import sys; import subprocess; p1 = os.path.dirname(sys.executable); print(p1); p = p1+"\\python3"; 
r =subprocess.run([p, "-m", "pip", "install", "specklepy==2.9.0"], capture_output=True, text=True, shell=True, timeout=1000); print(r) 
r =subprocess.run([p, "-m", "pip", "install", "panda3d==1.10.11"], capture_output=True, text=True, shell=True, timeout=1000); print(r) 
r =subprocess.run([p, "-m", "pip", "install", "pyshp==2.3.1"], capture_output=True, text=True, shell=True, timeout=1000); print(r) 
## IF retcode for EACH command is not 0: 
# - Windows -> cmd -> C:\Program Files\QGIS 3.28.0\bin
r'''
python -m pip install specklepy==2.9.0 
python -m pip install panda3d==1.10.11 
python -m pip install pyshp==2.3.1 
'''
# - restart QGIS 

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

