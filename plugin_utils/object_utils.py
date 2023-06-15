
import time
from typing import Any, Callable, List, Optional
from plugin_utils.helpers import removeSpecialCharacters 

from speckle.utils.panel_logging import logger
from qgis.core import Qgis, QgsProject
from specklepy.objects.GIS.layers import VectorLayer, RasterLayer, Layer
from speckle.converter.layers import geometryLayerToNative, layerToNative

import threading
from specklepy.objects import Base

from specklepy_qt_ui.logger import logToUser

SPECKLE_TYPES_TO_READ = ["Objects.Geometry.", "Objects.BuiltElements.", "IFC"] # will properly traverse and check for displayValue

def traverseObject(
    plugin,
    base: Base,
    callback: Optional[Callable[[Base, str, Any], bool]],
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
        if isinstance(base, VectorLayer) or isinstance(base, Layer) or isinstance(base, RasterLayer):
            layerToNative(base, streamBranch, plugin)
        else:
            loopObj(base, "", streamBranch, plugin, [])   
        return True 
    except: return 

def loopObj(base: Base, baseName: str, streamBranch: str, plugin, used_ids):
    try:
        memberNames = base.get_member_names()
        for name in memberNames:
            if name in ["id", "applicationId", "units", "speckle_type"]: continue
            # skip if traversal goes to displayValue of an object, that will be readable anyway:
            try: 
                if not isinstance(base, Base) and "Collection" not in base.speckle_type: continue
            except: 
                if not isinstance(base, Base): continue
            
            if (name == "displayValue" or name == "@displayValue") and base.speckle_type.startswith(tuple(SPECKLE_TYPES_TO_READ)): continue 

            try: 
                loopVal(base[name], baseName + "_" + name, streamBranch, plugin, used_ids)
            except: pass
    except: pass

def loopVal(value: Any, name: str, streamBranch: str, plugin, used_ids): # "name" is the parent object/property/layer name
    
    try: 
        name = removeSpecialCharacters(name)
        if isinstance(value, Base): 
            try: # loop through objects with Speckletype prop, but don't go through parts of Speckle Geometry object
                if not value.speckle_type.startswith("Objects.Geometry."): 
                    loopObj(value, name, streamBranch, plugin, used_ids)
                elif value.id not in used_ids: # if geometry
                    used_ids.append(value.id)
                    loopVal([value], name, streamBranch, plugin, used_ids)
            except: 
                loopObj(value, name, streamBranch, plugin, used_ids)

        elif isinstance(value, List):
            streamBranch = streamBranch.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")

            objectListConverted = 0
            for i, item in enumerate(value):
                used_ids.append(item.id)
                loopVal(item, name, streamBranch, plugin, used_ids)

                if not isinstance(item, Base): continue
                if "View" in item.speckle_type: continue
                if item.speckle_type and item.speckle_type.startswith("IFC"): 
                    # keep traversing infinitely, just don't run repeated conversion for the same list of objects
                    try: 
                        if item["displayValue"] is not None and objectListConverted == 0: 
                            geometryLayerToNative(value, name, streamBranch, plugin)
                            time.sleep(0.3)
                            objectListConverted += 1
                    except: 
                        try: 
                            if item["@displayValue"] is not None and objectListConverted == 0: 
                                geometryLayerToNative(value, name, streamBranch, plugin)
                                time.sleep(0.3)
                                objectListConverted += 1
                        except: pass 
                elif item.speckle_type and item.speckle_type.endswith(".ModelCurve"): 
                    if item["baseCurve"] is not None: 
                        geometryLayerToNative(value, name, streamBranch, plugin)
                        time.sleep(0.3)
                        break
                elif item.speckle_type and (item.speckle_type == "Objects.Geometry.Mesh" or item.speckle_type == "Objects.Geometry.Brep" or item.speckle_type.startswith("Objects.BuiltElements.")):
                    geometryLayerToNative(value, name, streamBranch, plugin)
                    time.sleep(0.3)
                    break
                elif item.speckle_type and item.speckle_type != "Objects.Geometry.Mesh" and item.speckle_type != "Objects.Geometry.Brep" and item.speckle_type.startswith("Objects.Geometry."): # or item.speckle_type == 'Objects.BuiltElements.Alignment'): 
                    geometryLayerToNative(value, name, streamBranch, plugin)
                    time.sleep(0.3)
                    break
                elif item.speckle_type:
                    try:
                        if item["baseLine"] is not None:
                            geometryLayerToNative(value, name, streamBranch, plugin)
                            time.sleep(0.3)
                            break
                    except: pass 
    except: pass 

