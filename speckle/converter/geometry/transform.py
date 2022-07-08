
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
    renderer = layer.renderer()
    try:
        if renderer.type() == 'categorizedSymbol' or renderer.type() == '25dRenderer' or renderer.type() == 'invertedPolygonRenderer' or renderer.type() == 'mergedFeatureRenderer' or renderer.type() == 'RuleRenderer' or renderer.type() == 'nullSymbol' or renderer.type() == 'singleSymbol' or renderer.type() == 'graduatedSymbol':
            #get color value
            color = QColor.fromRgb(0,0,0)
            if renderer.type() == 'singleSymbol':
                color = renderer.symbol().color()
            elif renderer.type() == 'categorizedSymbol':
                color = renderer.sourceSymbol().color()
                category = renderer.classAttribute() # get the name of attribute used for classification
                for obj in renderer.categories():
                    if str(obj.value()) == str(feature.attribute( category )): 
                        color = obj.symbol().color()
                        break
            elif renderer.type() == 'graduatedSymbol':
                color = renderer.sourceSymbol().color()
                category = renderer.legendClassificationAttribute() # get the name of attribute used for classification
                if renderer.graduatedMethod() == 0: #if the styling is by color (not by size)
                    for obj in renderer.ranges():
                        if feature.attribute( category ) >= obj.lowerValue() and feature.attribute( category ) <= obj.upperValue(): 
                            color = obj.symbol().color()
                            break
            # construct RGB color
            try: r, g, b = color.getRgb()[:3]
            except: r, g, b = [int(i) for i in color.replace(" ","").split(",")[:3] ]
            #rVal = color.red(); gVal = color.green(); bVal = color.blue()
            #except: rVal = 0; gVal = 0; bVal = 0
            col = (r<<16) + (g<<8) + b
            return col
        else:
            return (0<<16) + (0<<8) + 0
    except:
        return (0<<16) + (0<<8) + 0
