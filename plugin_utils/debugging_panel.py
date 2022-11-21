
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
