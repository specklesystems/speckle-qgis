
import time
from typing import Any, Callable, List, Optional 

from speckle.logging import logger
from qgis.core import Qgis, QgsProject
from speckle.converter.layers.Layer import VectorLayer, RasterLayer, Layer
from speckle.converter.layers import bimLayerToNative, cadLayerToNative, layerToNative

import threading
from specklepy.objects import Base

from ui.logger import logToUser

SPECKLE_TYPES_TO_READ = ["Objects.Geometry.", "Objects.BuiltElements.", "IFC"] # will properly traverse and check for displayValue

def traverseObject(
    plugin,
    base: Base,
    callback: Optional[Callable[[Base, str, QgsProject], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
):
    if check and check(base):
        res = callback(base, streamBranch, plugin) if callback else False
        if res:
            return
    memberNames = base.get_member_names()
    for name in memberNames:
        try:
            if ["id", "applicationId", "units", "speckle_type"].index(name):
                continue
        except:
            pass
        traverseValue(plugin, base[name], callback, check, streamBranch)
        #time.sleep(0.3)
    
    #logToUser("DATA RECEIVED", level=0, plugin = plugin)
    #logger.logToUser("DATA RECEIVED", Qgis.Info)

def traverseValue(
    plugin,
    value: Any,
    callback: Optional[Callable[[Base, str, Any], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
):
    if isinstance(value, Base):
        traverseObject(plugin, value, callback, check, streamBranch)
    if isinstance(value, List):
        for item in value:
            traverseValue(plugin, item, callback, check, streamBranch)


def callback(base: Base, streamBranch: str, plugin) -> bool:
    try:
        project: QgsProject = plugin.qgis_project
        if isinstance(base, VectorLayer) or isinstance(base, Layer) or isinstance(base, RasterLayer):
            #print(base)
            #if isinstance(base, Layer):
            #    logger.log(f"Class \"Layer\" will be deprecated in future updates in favour of \"VectorLayer\" or \"RasterLayer\"", Qgis.Warning) 
            layerToNative(base, streamBranch, plugin)
            time.sleep(0.3)
            #if layer is not None:
            #    .logToUser("Layer created: " + layer.name(), Qgis.Info)
        else:
            loopObj(base, "", streamBranch, plugin)    
    except: pass
    return True

def loopObj(base: Base, baseName: str, streamBranch: str, plugin):
    try:
        project: QgsProject = plugin.project_qgis
        memberNames = base.get_member_names()
        for name in memberNames:
            if name in ["id", "applicationId", "units", "speckle_type"]: continue
            # skip if traversal goes to displayValue of an object, that will be readable anyway:
            if not isinstance(base, Base): continue
            if (name == "displayValue" or name == "@displayValue") and base.speckle_type.startswith(tuple(SPECKLE_TYPES_TO_READ)): continue 

            try: loopVal(base[name], baseName + "/" + name, streamBranch, plugin)
            except: pass
    except: pass

def loopVal(value: Any, name: str, streamBranch: str, plugin): # "name" is the parent object/property/layer name

    try: 
        project: QgsProject = plugin.project_qgis
        if isinstance(value, Base): 
            try: # loop through objects with Speckletype prop, but don't go through parts of Speckle Geometry object
                if not value.speckle_type.startswith("Objects.Geometry."): 
                    loopObj(value, name, streamBranch, plugin)
            except: 
                loopObj(value, name, streamBranch, plugin)

        elif isinstance(value, List):
            streamBranch = streamBranch.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")

            objectListConverted = 0
            for i, item in enumerate(value):
                loopVal(item, name, streamBranch, plugin)
                if not isinstance(item, Base): continue
                if item.speckle_type and item.speckle_type.startswith("IFC"): 
                    # keep traversing infinitely, just don't run repeated conversion for the same list of objects
                    try: 
                        if item["displayValue"] is not None and objectListConverted == 0: 
                            bimLayerToNative(value, name, streamBranch, plugin)
                            time.sleep(0.3)
                            objectListConverted += 1
                    except: 
                        try: 
                            if item["@displayValue"] is not None and objectListConverted == 0: 
                                bimLayerToNative(value, name, streamBranch, plugin)
                                time.sleep(0.3)
                                objectListConverted += 1
                        except: pass 
                elif item.speckle_type and item.speckle_type.endswith(".ModelCurve"): 
                    if item["baseCurve"] is not None: 
                        cadLayerToNative(value, name, streamBranch, plugin)
                        time.sleep(0.3)
                        break
                elif item.speckle_type and item["baseLine"] is not None:
                    cadLayerToNative(value, name, streamBranch, plugin)
                    time.sleep(0.3)
                    break
                elif item.speckle_type and (item.speckle_type == "Objects.Geometry.Mesh" or item.speckle_type == "Objects.Geometry.Brep" or item.speckle_type.startswith("Objects.BuiltElements.")):
                    bimLayerToNative(value, name, streamBranch, plugin)
                    time.sleep(0.3)
                    break
                elif item.speckle_type and item.speckle_type != "Objects.Geometry.Mesh" and item.speckle_type != "Objects.Geometry.Brep" and item.speckle_type.startswith("Objects.Geometry."): # or item.speckle_type == 'Objects.BuiltElements.Alignment'): 
                    pt, pl = cadLayerToNative(value, name, streamBranch, plugin)
                    time.sleep(0.3)
                    #if pt is not None: logger.log("Layer group created: " + str(pt.name()))
                    #if pl is not None: logger.log("Layer group created: " + str(pl.name()))
                    break
    except: pass 

