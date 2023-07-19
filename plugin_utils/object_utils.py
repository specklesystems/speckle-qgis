
import time
import numpy as np
from typing import Any, Callable, List, Optional
from plugin_utils.helpers import SYMBOL, removeSpecialCharacters 

from specklepy.objects.GIS.layers import VectorLayer, RasterLayer, Layer
from speckle.converter.layers import geometryLayerToNative, layerToNative

import threading
from specklepy.objects import Base

from speckle.converter.layers.utils import findUpdateJsonItemPath


SPECKLE_TYPES_TO_READ = ["Objects.Geometry.", "Objects.BuiltElements.", "IFC"] # will properly traverse and check for displayValue

def traverseObject(
    plugin,
    base: Base,
    callback: Optional[Callable[[Base, str, Any], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
    nameBase: str = ""
):
    print("___traverseObject")
    if check and check(base):
        res = callback(base, streamBranch, nameBase, plugin) if callback else False
        if res:
            return
    memberNames = base.get_member_names()
    for name in memberNames:
        print("for name in memberNames:")
        try:
            if ["id", "applicationId", "units", "speckle_type"].index(name):
                continue
        except:
            pass
        
        if nameBase == SYMBOL + "QGIS commit":
            name_pass = getBaseValidName(base, name)
        else: 
            name_pass = nameBase + SYMBOL + getBaseValidName(base, name)
        # check again 
        if name_pass == SYMBOL + "QGIS commit": name_pass = ""
        print(name_pass)
        traverseValue(plugin, base[name], callback, check, streamBranch, name_pass)


def traverseValue(
    plugin,
    value: Any,
    callback: Optional[Callable[[Base, str, Any], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
    name: str,
):
    print("________traverseValue")
    if isinstance(value, Base):
        traverseObject(plugin, value, callback, check, streamBranch, name)
    if isinstance(value, List):
        for item in value:
            traverseValue(plugin, item, callback, check, streamBranch, name)

def callback(base: Base, streamBranch: str, nameBase: str, plugin) -> bool:
    print("___CALLBACK")
    print(nameBase)
    try:
        if isinstance(base, VectorLayer) or isinstance(base, Layer) or isinstance(base, RasterLayer) or base.speckle_type.endswith("VectorLayer") or base.speckle_type.endswith("RasterLayer"):
            layerToNative(base, streamBranch, nameBase, plugin)
        else:
            loopObj(base, "", streamBranch, plugin, [])   
        return True 
    except: return 

def getBaseValidName(base: Base, name: str) -> str:
    name_pass = name
    search = 0
    try:
        if (name == "elements" and isinstance(base[name], list)):
            search = 1
    except: pass
    try:
        if (name == "displayValue" or name == "@displayValue"):
            search = 1
    except: pass 
    try:
        if (name == "definition" and isinstance(base[name], Base)):
            search = 1
    except: pass

    try: 
        if search == 1:
            try: 
                if (base["name"], str) and len(base["name"])>1 and base["name"]!="null": name_pass = base["name"]
                else: raise Exception
            except: 
                try: 
                    if (base["Name"], str) and len(base["Name"])>1 and base["Name"]!="null": name_pass = base["Name"]
                    else: raise Exception
                except: 
                    try: 
                        if (base["type"], str) and len(base["type"])>1 and base["type"]!="null": name_pass = base["type"]
                        else: raise Exception
                    except: 
                        try: 
                            if (base["category"], str) and len(base["category"])>1 and base["category"]!="null": name_pass = base["category"]
                            else: raise Exception
                        except: name_pass = name 
    except Exception as e: print(e)
    return name_pass

def loopObj(base: Base, baseName: str, streamBranch: str, plugin, used_ids, matrix = None):
    try:
        # dont loop primitives 
        if not isinstance(base, Base): return

        memberNames = base.get_member_names()
        
        baseName_pass = removeSpecialCharacters(baseName)
        #print(plugin.receive_layer_tree)
        plugin.receive_layer_tree = findUpdateJsonItemPath(plugin.receive_layer_tree, streamBranch + SYMBOL + baseName_pass)
        #print(plugin.receive_layer_tree)

        for name in memberNames:
            if name in ["id", "applicationId", "units", "speckle_type"]: 
                continue
            # skip if traversal goes to displayValue of an object, that will be readable anyway:
            
            if (name == "displayValue" or name == "@displayValue") and base.speckle_type.startswith(tuple(SPECKLE_TYPES_TO_READ)): 
                continue 
            
            try: 
                if "View" in base[name].speckle_type or "RevitMaterial" in base[name].speckle_type: continue
            except: pass
            
            name_pass = baseName_pass + SYMBOL + getBaseValidName(base, name)
            
            if base[name] is not None:
                if name.endswith("definition"):
                    try:
                        matrixList = base["transform"].matrix
                        try:
                            matrix2 = np.matrix(matrixList).reshape(4, 4)
                            matrix2 = matrix2.transpose()
                            if matrix2 is None:
                                geometryLayerToNative([base[name]], name, streamBranch, plugin, None)
                                
                            else: # both not None 
                                if matrix is not None: 
                                    matrix = matrix2 * matrix
                                else: # matrix is None 
                                    matrix = matrix2
                                geometryLayerToNative([base[name]], name_pass, streamBranch, plugin, matrix)

                        except: matrix = None
                        time.sleep(0.3)
                    except Exception as e: print(f"ERROR: {e}") 
                loopVal(base[name], name_pass, streamBranch, plugin, used_ids, matrix)     
    except Exception as e: print(e) 

def loopVal(value: Any, name: str, streamBranch: str, plugin, used_ids, matrix = None): # "name" is the parent object/property/layer name
    
    try: 
        name = removeSpecialCharacters(name)
        if isinstance(value, Base): 
            try: # loop through objects with Speckletype prop, but don't go through parts of Speckle Geometry object
                
                if "View" in value.speckle_type or "RevitMaterial" in value.speckle_type: return

                if not value.speckle_type.startswith("Objects.Geometry."): 
                    loopObj(value, name, streamBranch, plugin, used_ids, matrix)
                elif value.id not in used_ids: # if geometry
                    used_ids.append(value.id)
                    loopVal([value], name, streamBranch, plugin, used_ids, matrix)
            except: 
                loopObj(value, name, streamBranch, plugin, used_ids, matrix)

        elif isinstance(value, List):
            print("LOOP VAL - LIST")
            streamBranch = removeSpecialCharacters(streamBranch)

            objectListConverted = 0
            for i, item in enumerate(value):
                used_ids.append(item.id)
                loopVal(item, name, streamBranch, plugin, used_ids, matrix)

                if not isinstance(item, Base): continue
                if "View" in item.speckle_type or "RevitMaterial" in item.speckle_type: continue

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
