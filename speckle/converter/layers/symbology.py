
import inspect
from typing import Any, Union
from qgis.core import (
    QgsRasterRenderer, QgsFeatureRenderer, QgsFields,
    QgsFeature, QgsVectorLayer,
    QgsGradientColorRamp, 
    QgsGradientStop, QgsRendererRange,
    QgsSingleBandGrayRenderer, 
    QgsPalettedRasterRenderer, QgsMultiBandColorRenderer,
    QgsContrastEnhancement,
    QgsSymbol, QgsWkbTypes, QgsRendererCategory,
    QgsCategorizedSymbolRenderer, QgsSingleSymbolRenderer,
    QgsGraduatedSymbolRenderer, QgsRasterDataProvider

)
from speckle.converter.layers.Layer import Layer, RasterLayer, VectorLayer
from PyQt5.QtGui import QColor

from ui.logger import logToUser

# TODO QML format: https://gis.stackexchange.com/questions/202230/loading-style-qml-file-to-layer-via-pyqgis 

def featureColorfromNativeRenderer(feature: QgsFeature, layer: QgsVectorLayer) -> int:
    # case with one color for the entire layer
    try:
        renderer = layer.renderer()
        if renderer.type() == 'categorizedSymbol' or renderer.type() == '25dRenderer' or renderer.type() == 'invertedPolygonRenderer' or renderer.type() == 'mergedFeatureRenderer' or renderer.type() == 'RuleRenderer' or renderer.type() == 'nullSymbol' or renderer.type() == 'singleSymbol' or renderer.type() == 'graduatedSymbol':
            #get color value
            color = QColor.fromRgb(245,245,245)
            if renderer.type() == 'singleSymbol':
                color = renderer.symbol().color()
            elif renderer.type() == 'categorizedSymbol':
                sSymb = renderer.sourceSymbol()
                if sSymb is not None: color = sSymb.color()
                category = renderer.classAttribute() # get the name of attribute used for classification
                for obj in renderer.categories():
                    try: 
                        if float(obj.value()) == float(feature.attribute( category )):
                            color = obj.symbol().color()
                            break
                    except:
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
            col = (r<<16) + (g<<8) + b
            return col
        else: return (245<<16) + (245<<8) + 245
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return (245<<16) + (245<<8) + 245

def gradientColorRampToSpeckle(rRamp: QgsGradientColorRamp) -> dict[str, Any]: 
    sourceRamp = None
    try:
        props = rRamp.properties() # {'color1': '255,255,255,255', 'color2': '255,0,0,255', 'discrete': '0', 'rampType': 'gradient'}
        stops = rRamp.stops() #[]
        stopsStr = []
        for s in stops:
            try: r, g, b = s.color.getRgb()[:3]
            except: r, g, b = [int(i) for i in s.color.replace(" ","").split(',')[:3] ]
            sColor = (r<<16) + (g<<8) + b
            stopsStr.append({'color':sColor, 'offset':s.offset})
        rampType = rRamp.type() #'gradient'
        sourceRamp = props
        sourceRamp.update({'stops': stopsStr, 'rampType':rampType})

        return sourceRamp
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return sourceRamp

def gradientColorRampToNative(renderer: dict[str, Any]) -> QgsGradientColorRamp:

    newRamp = None
    try: # if it's not a random color ramp
        ramp = renderer['properties']['ramp'] # {discrete, rampType, stops}
        oldStops = ramp['stops']
        stops = []
        for i in range(len(oldStops)):
            rgb = oldStops[i]['color']
            r = (rgb & 0xFF0000) >> 16
            g = (rgb & 0xFF00) >> 8
            b = rgb & 0xFF 
            sColor = QColor.fromRgb(r, g, b)
            s = QgsGradientStop(oldStops[i]['offset'], sColor)
            stops.append(s)

        c11,c12,c13,alpa1 = ramp['color1'].split(',')
        color1 = QColor.fromRgb(int(c11),int(c12),int(c13))
        c21,c22,c23,alpha2 = ramp['color2'].split(',')
        color2 = QColor.fromRgb(int(c21),int(c22),int(c23))
        discrete = int(ramp['discrete'])
        newRamp = QgsGradientColorRamp(color1,color2,discrete,stops)

        return newRamp
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return newRamp

def get_r_g_b(rgb: int) -> tuple[int, int, int]:
    r = g = b = 0
    try: 
        r = (rgb & 0xFF0000) >> 16
        g = (rgb & 0xFF00) >> 8
        b = rgb & 0xFF 
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return 0,0,0

def vectorRendererToNative(layer: Union[Layer, VectorLayer], fields: QgsFields ) -> Union[QgsSingleSymbolRenderer,QgsCategorizedSymbolRenderer, QgsGraduatedSymbolRenderer]:
    
    rendererNew = None
    try:
        renderer = layer.renderer 
        existingAttrs = fields.names()
        geomType = layer.geomType
        if geomType == 'MultiPatch': geomType = "Polygon"

        if "polyline" in geomType.lower(): geomType = 'LineString'
        if renderer and renderer['type']:

            if renderer['type']  == 'categorizedSymbol':
                try: r,g,b = get_r_g_b(renderer['properties']['sourceSymbColor']) 
                except: r = g = b = 100 
                sourceSymbColor = QColor.fromRgb(r, g, b)

                attribute = renderer['properties']['attribute']
                cats = renderer['properties']['categories']
                if attribute not in existingAttrs: 
                    rendererNew = makeDefaultRenderer(renderer, layer)
                    return rendererNew
                categories = []
                noneVal = 0
                for i in range(len(cats)):
                    v = cats[i]['value'] 
                    if v=="<Null>": v = None
                    if v is None or v=="": noneVal +=1
                    rgb = cats[i]['symbColor']
                    r = (rgb & 0xFF0000) >> 16
                    g = (rgb & 0xFF00) >> 8
                    b = rgb & 0xFF 
                    color = QColor.fromRgb(r, g, b)
                    symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
                    # create an extra category for possible future feature
                    #if len(categories)==0: 
                    #    symbol.setColor(QColor.fromRgb(0,0,0))
                    #    categories.append(QgsRendererCategory())
                    #    categories[0].setSymbol(symbol)
                    #    categories[0].setLabel('Other')

                    symbol.setColor(color)
                    categories.append(QgsRendererCategory(v, symbol, cats[i]['label'], True) )
                # create empty category for all other values (if doesn't exist yet)
                if noneVal == 0:
                    symbol2 = symbol.clone()
                    symbol2.setColor(QColor.fromRgb(0,0,0))
                    cat = QgsRendererCategory()
                    cat.setSymbol(symbol2)
                    cat.setLabel('Other')
                    categories.append(cat)
                
                rendererNew = QgsCategorizedSymbolRenderer(attribute, categories)
                try:
                    sourceSymbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
                    sourceSymbol.setColor(sourceSymbColor)
                    rendererNew.setSourceSymbol(sourceSymbol)
                except: pass

            elif renderer['type'] == 'singleSymbol':
                rgb = renderer['properties']['symbol']['symbColor']
                r = (rgb & 0xFF0000) >> 16
                g = (rgb & 0xFF00) >> 8
                b = rgb & 0xFF 
                color = QColor.fromRgb(r, g, b)
                symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
                symbol.setColor(color)
                rendererNew = QgsSingleSymbolRenderer(symbol)
            
            elif renderer['type'] == 'graduatedSymbol':
                attribute = renderer['properties']['attribute']
                gradMetod = renderer['properties']['gradMethod'] # by color or by size
                if attribute not in existingAttrs: 
                    rendererNew = makeDefaultRenderer(renderer, layer)
                    return rendererNew

                rgb = renderer['properties']['sourceSymbColor'] 
                r = (rgb & 0xFF0000) >> 16
                g = (rgb & 0xFF00) >> 8
                b = rgb & 0xFF 
                sourceSymbColor = QColor.fromRgb(r, g, b)
                
                if gradMetod == 0:
                    ramp = renderer['properties']['ramp'] # {discrete, rampType, stops}
                    ranges = renderer['properties']['ranges'] # []
                    newRamp = gradientColorRampToNative(renderer) #QgsGradientColorRamp

                    newRanges = []
                    for i in range(len(ranges)):
                        rgb = ranges[i]['symbColor']
                        r = (rgb & 0xFF0000) >> 16
                        g = (rgb & 0xFF00) >> 8
                        b = rgb & 0xFF 
                        color = QColor.fromRgb(r, g, b)
                        width = ranges[i]['symbColor']
                        symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
                        symbol.setColor(color)
                        newRanges.append(QgsRendererRange(ranges[i]['lower'],ranges[i]['upper'],symbol,ranges[i]['label'],True) )
                    try: 
                        rendererNew = QgsGraduatedSymbolRenderer(attribute, newRanges)
                        rendererNew.setSourceColorRamp(newRamp)
                        sourceSymbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
                        sourceSymbol.setColor(sourceSymbColor)
                        rendererNew.setSourceSymbol(sourceSymbol)
                    except: rendererNew = QgsGraduatedSymbolRenderer()
                    try: rendererNew.setGraduatedMethod(gradMetod)
                    except:  rendererNew.setGraduatedMethod(QgsGraduatedSymbolRenderer.GraduatedMethod(gradMetod))
                else:
                    rendererNew = makeDefaultRenderer(renderer, layer)

        return rendererNew
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return rendererNew

def makeDefaultRenderer(renderer: dict[str, Any], layer: Union[Layer, VectorLayer]) -> QgsSingleSymbolRenderer:
    rendererNew = None 
    try:
        geomType = layer.geomType
        try: rgb = renderer['properties']['sourceSymbColor']
        except: rgb = (0<<16) + (0<<8) + 0
        r = (rgb & 0xFF0000) >> 16
        g = (rgb & 0xFF00) >> 8
        b = rgb & 0xFF 
        color = QColor.fromRgb(r, g, b)
        symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
        symbol.setColor(color)
        rendererNew = QgsSingleSymbolRenderer(symbol)
        return rendererNew
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return rendererNew

def rasterRendererToNative(layer: RasterLayer, rInterface: QgsRasterDataProvider) -> Union[QgsSingleBandGrayRenderer, QgsMultiBandColorRenderer, QgsPalettedRasterRenderer]:
    
    rendererNew = None
    try:
        renderer = layer.renderer
        if renderer and renderer['type']:
            if renderer['type']  == 'singlebandgray':
                band = renderer['properties']['band']
                contrast = QgsContrastEnhancement()
                contrast.setContrastEnhancementAlgorithm(int(renderer['properties']['contrast']))
                contrast.setMaximumValue(float(renderer['properties']['max']))
                contrast.setMinimumValue(float(renderer['properties']['min']))
                
                rendererNew = QgsSingleBandGrayRenderer(rInterface,int(band))
                rendererNew.setContrastEnhancement(contrast)

            if renderer['type']  == 'multibandcolor':
                redBand = renderer['properties']['redBand']
                greenBand = renderer['properties']['greenBand']
                blueBand = renderer['properties']['blueBand']
                rendererNew = QgsMultiBandColorRenderer(rInterface,int(redBand),int(greenBand),int(blueBand))
                try:
                    contrastR = QgsContrastEnhancement()
                    contrastR.setContrastEnhancementAlgorithm(int(renderer['properties']['redContrast']))
                    contrastR.setMaximumValue(float(renderer['properties']['redMax']))
                    contrastR.setMinimumValue(float(renderer['properties']['redMin']))
                    #rendererNew.setRedContrastEnhancement(contrastR)
                except: pass
                try:
                    contrastG = QgsContrastEnhancement()
                    contrastG.setContrastEnhancementAlgorithm(int(renderer['properties']['greenContrast']))
                    contrastG.setMaximumValue(float(renderer['properties']['greenMax']))
                    contrastG.setMinimumValue(float(renderer['properties']['greenMin']))
                    #rendererNew.setGreenContrastEnhancement(contrastG)
                except: pass
                try:
                    contrastB = QgsContrastEnhancement()
                    contrastB.setContrastEnhancementAlgorithm(int(renderer['properties']['blueContrast']))
                    contrastB.setMaximumValue(float(renderer['properties']['blueMax']))
                    contrastB.setMinimumValue(float(renderer['properties']['blueMin']))
                    #rendererNew.setBlueContrastEnhancement(contrastB)
                except: pass

            if renderer['type']  == 'paletted':
                band = renderer['properties']['band']
                classes = renderer['properties']['classes']
                #newRamp = gradientColorRampToNative(renderer) #QgsGradientColorRamp
                newClasses = []
                for i in classes:
                    rgb = i['color']
                    r = (rgb & 0xFF0000) >> 16
                    g = (rgb & 0xFF00) >> 8
                    b = rgb & 0xFF 
                    color = QColor.fromRgb(r, g, b)
                    newClasses.append(QgsPalettedRasterRenderer.Class(float(i['value']),color,i['label']))

                rendererNew = QgsPalettedRasterRenderer(rInterface,int(band),newClasses)
        return rendererNew
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return rendererNew
    
def rendererToSpeckle(renderer: QgsFeatureRenderer or QgsRasterRenderer) -> dict[str, Any]:

    layerRenderer: dict[str, Any] = {}
    try:
        #print("___RENDERER TO SPECKLE___")
        rType = renderer.type() # 'singleSymbol','categorizedSymbol','graduatedSymbol',
        layerRenderer['type'] = rType

        if rType == 'singleSymbol': 
            layerRenderer['properties'] = {'symbol':{}, 'symbType':""}

            symbol = renderer.symbol() #singleSymbol # QgsLineSymbol
            #print(symbol)
            symbType = symbol.symbolTypeToString(symbol.type()) #Line
            try: rgb = symbol.color().getRgb()
            except: [int(i) for i in symbol().color().replace(" ","").split(',')[:3] ]
            symbolColor = (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
            layerRenderer['properties'].update({'symbol':{'symbColor': symbolColor}, 'symbType':symbType})

        elif rType == 'categorizedSymbol': 
            layerRenderer['properties'] = {'attribute': "", 'symbType': ""} #{'symbol':{}, 'ramp':{}, 'ranges':{}, 'gradMethod':"", 'symbType':"", 'legendClassificationAttribute': ""}
            attribute = renderer.classAttribute() # 'id'
            layerRenderer['properties']['attribute'] = attribute
            symbol = renderer.sourceSymbol()
            sourceSymbColor = (0<<16) + (0<<8) + 0
            try:
                symbType = symbol.symbolTypeToString(symbol.type()) #Line
                try: r, g, b = symbol.color().getRgb()[:3]
                except: r,g,b = [int(i) for i in symbol.color().replace(" ","").split(',')[:3] ]
                sourceSymbColor = (r<<16) + (g<<8) + b

                layerRenderer['properties'].update( {'symbType': symbType, 'sourceSymbColor': sourceSymbColor} )
            except: pass
            
            categories = renderer.categories() #<qgis._core.QgsRendererCategory object at 0x00000155E8786A60>
            layerRenderer['properties']['categories'] = []
            for i in categories:
                value = i.value()
                try: r, g, b = i.symbol().color().getRgb()[:3]
                except: r,g,b = [int(i) for i in i.symbol().color().replace(" ","").split(',')[:3] ]
                symbColor = (r<<16) + (g<<8) + b
                symbOpacity = i.symbol().opacity() # QgsSymbol.color()
                label = i.label() 
                layerRenderer['properties']['categories'].append({'value':value,'symbColor':symbColor,'symbOpacity':symbOpacity, 'sourceSymbColor': sourceSymbColor,'label':label})
                
        elif rType == 'graduatedSymbol': 
            layerRenderer['properties'] = {'symbol':{}, 'ramp':{}, 'ranges':{}, 'gradMethod':"", 'symbType':""}

            attribute = renderer.legendClassificationAttribute() # 'id'
            symbol = renderer.sourceSymbol() # QgsLineSymbol
            symbType = symbol.symbolTypeToString(symbol.type()) #Line
            try: r, g, b = symbol.color().getRgb()[:3]
            except: r, g, b = [int(i) for i in symbol.color().replace(" ","").split(',')[:3] ]
            sourceSymbColor = (r<<16) + (g<<8) + b
            gradMethod = renderer.graduatedMethod() # 0
            layerRenderer['properties'].update( {'attribute': attribute, 'symbType': symbType, 'gradMethod': gradMethod, 'sourceSymbColor': sourceSymbColor} )

            rRamp = renderer.sourceColorRamp() # QgsGradientColorRamp
            if isinstance(rRamp,QgsGradientColorRamp) : 
                layerRenderer['properties']['ramp'] = gradientColorRampToSpeckle(rRamp)

            rRanges = renderer.ranges() # [QgsRendererRange,...]
            layerRenderer['properties']['ranges'] = []
            for i in rRanges:
                if isinstance(i, QgsRendererRange):
                    lower = i.lowerValue()
                    upper = i.upperValue()
                    rgb = i.symbol().color().getRgb() # QgsSymbol.color() -> QColor
                    symbColor = (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
                    symbOpacity = i.symbol().opacity() # QgsSymbol.color()
                    label = i.label() 
                    width = 0.26
                    try: width = i.width()
                    except: pass
                    # {'label': '1 - 1.4', 'lower': 1.0, 'symbColor': <PyQt5.QtGui.QColor ...BD9B9D4A0>, 'symbOpacity': 1.0, 'upper': 1.4}
                    layerRenderer['properties']['ranges'].append({'lower':lower,'upper':upper,'symbColor':symbColor,'symbOpacity':symbOpacity,'label':label,'width':width})
        
        elif rType == "singlebandgray":  
            band = renderer.grayBand()
            contrast = renderer.contrastEnhancement().contrastEnhancementAlgorithm()
            mmin = renderer.contrastEnhancement().minimumValue()
            mmax = renderer.contrastEnhancement().maximumValue()
            layerRenderer.update({'properties': {'max':mmax,'min':mmin,'band':band,'contrast':contrast}})
        elif rType == "multibandcolor":  
            redBand = renderer.redBand()
            greenBand = renderer.greenBand()
            blueBand = renderer.blueBand() 
            redContrast = redMin = redMax = greenContrast = greenMin = greenMax = blueContrast = blueMin = blueMax = None
            try:
                redContrast = renderer.redContrastEnhancement().contrastEnhancementAlgorithm()
                redMin = renderer.redContrastEnhancement().minimumValue()
                redMax = renderer.redContrastEnhancement().maximumValue()
            except: pass
            try:
                greenContrast = renderer.greenContrastEnhancement().contrastEnhancementAlgorithm()
                greenMin = renderer.greenContrastEnhancement().minimumValue()
                greenMax = renderer.greenContrastEnhancement().maximumValue()
            except: pass
            try:
                blueContrast = renderer.blueContrastEnhancement().contrastEnhancementAlgorithm()
                blueMin = renderer.blueContrastEnhancement().minimumValue()
                blueMax = renderer.blueContrastEnhancement().maximumValue()
            except: pass
            layerRenderer.update({'properties': {'greenBand':greenBand,'blueBand':blueBand,'redBand':redBand}})
            layerRenderer['properties'].update({'redContrast':redContrast,'redMin':redMin,'redMax':redMax})
            layerRenderer['properties'].update({'greenContrast':greenContrast,'greenMin':greenMin,'greenMax':greenMax})
            layerRenderer['properties'].update({'blueContrast':blueContrast,'blueMin':blueMin,'blueMax':blueMax})

        elif rType == "paletted":  
            band = renderer.band()
            rendererClasses = renderer.classes()
            classes = []
            rRamp = renderer.sourceColorRamp()
            sourceRamp = {}
            if isinstance(rRamp,QgsGradientColorRamp) : # or QgsRandomColorRamp
                sourceRamp = gradientColorRampToSpeckle(rRamp) #rampType, stops,props(e.g.color)

            for i in rendererClasses:
                value = i.value 
                rgb = i.color.getRgb()
                color =  (rgb[0]<<16) + (rgb[1]<<8) + rgb[2]
                classes.append({'color':color,'value':value,'label':i.label})
            layerRenderer.update({'properties': {'classes':classes,'ramp':sourceRamp,'band':band}})
            
        else: 
            layerRenderer = {'type': 'Other', 'properties': {}}
        return layerRenderer
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return layerRenderer


