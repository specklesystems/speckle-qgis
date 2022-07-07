
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,  QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    Qgis, QgsWkbTypes, QgsPolygon, QgsPointXY, QgsPoint, QgsFeature, QgsVectorLayer
)

from PyQt5.QtGui import QColor


def transform(
    src: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the source CRS to the destination."""

    transformContext = QgsProject.instance().transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

    # forward transformation: src -> dest
    dest = xform.transform(src)
    return dest


def reverseTransform(
    dest: QgsPointXY,
    crsSrc: QgsCoordinateReferenceSystem,
    crsDest: QgsCoordinateReferenceSystem,
):
    """Transforms a QgsPointXY from the destination CRS to the source."""

    transformContext = QgsProject.instance().transformContext()
    xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

    # inverse transformation: dest -> src
    src = xform.transform(dest, QgsCoordinateTransform.ReverseTransform)
    return src

def featureColorfromNativeRenderer(feature: QgsFeature, layer: QgsVectorLayer):
    # case with one color for the entire layer
    try:
        if layer.renderer().type() == 'categorizedSymbol' or layer.renderer().type() == '25dRenderer' or layer.renderer().type() == 'invertedPolygonRenderer' or layer.renderer().type() == 'mergedFeatureRenderer' or layer.renderer().type() == 'RuleRenderer' or layer.renderer().type() == 'nullSymbol' or layer.renderer().type() == 'singleSymbol' or layer.renderer().type() == 'graduatedSymbol':
            #get color value
            color = QColor.fromRgb(0,0,0)
            if layer.renderer().type() == 'singleSymbol':
                color = layer.renderer().symbol().color()
            elif layer.renderer().type() == 'categorizedSymbol':
                category = layer.renderer().classAttribute() # get the name of attribute used for classification
                for obj in layer.renderer().categories():
                    if str(obj.value()) == str(feature.attribute( category )): 
                        color = obj.symbol().color()
                        break
            elif layer.renderer().type() == 'graduatedSymbol':
                category = layer.renderer().legendClassificationAttribute() # get the name of attribute used for classification
                for obj in layer.renderer().ranges():
                    if feature.attribute( category ) >= obj.lowerValue() and feature.attribute( category ) <= obj.upperValue(): 
                        color = obj.symbol().color()
                        break
            # construct RGB color
            rVal = color.red(); gVal = color.green(); bVal = color.blue()
            #except: rVal = 0; gVal = 0; bVal = 0
            col = (rVal<<16) + (gVal<<8) + bVal
            return col
        else:
            return (0<<16) + (0<<8) + 0
    except:
        return (0<<16) + (0<<8) + 0
