
import time
from typing import Any, Callable, List, Optional, Tuple 

from speckle.logging import logger
from qgis.core import Qgis, QgsProject
from speckle.converter.layers.Layer import VectorLayer, RasterLayer, Layer
from speckle.converter.layers import bimLayerToNative, cadLayerToNative, layerToNative

import threading
from specklepy.objects import Base
from specklepy.api.wrapper import StreamWrapper
from speckle.notifications.utils import TABLE_ATTRS

from ui.logger import logToUser
from ui.validation import tryGetObject

def traverseObj(sw: StreamWrapper, base: Base, attrs: List) -> dict:
    object = {}

    # create properties with start values for the object 
    for (name_attr, type_attr, result_attr) in TABLE_ATTRS:
        object[name_attr] = result_attr
    
    object = loopObj(sw, object, base, attrs) 
    return object

def loopObj(sw: StreamWrapper, object: dict, baseToTraverse: Base, attrs: List) -> dict:
    try:
        if isinstance(baseToTraverse, List): 
            for item in baseToTraverse:
                print(item)
                object = loopObj(sw, object, item, attrs)
        
        elif isinstance(baseToTraverse, Base): 
            if baseToTraverse.speckle_type == "reference":
                new_base: Base = tryGetObject(sw = sw, ref_id = baseToTraverse["referencedId"])
                object = loopObj(sw, object, new_base, attrs)
            elif "datachunk" in baseToTraverse.speckle_type.lower():
                pass
            else:
                memberNames = baseToTraverse.get_member_names()
                for name in memberNames:
                    if name in ["id", "applicationId", "units", "speckle_type", "totalChildrenCount", "@Standard Views", "displayValue", "@displayValue", "displayStyle", "@displayStyle", "renderMaterial"]: continue
                                    
                    else:
                        if name in [x[0] for x in TABLE_ATTRS]:
                            for (name_attr, type_attr, result_attr) in TABLE_ATTRS:
                                if name == name_attr or ("@"+name) == name_attr:

                                    if "area" in name: #type_attr == 6:
                                        try:
                                            object[name] += float(baseToTraverse[name])
                                        except Exception as e: print(e) 
                                    
                                    elif "value" in name: #type_attr == 10:
                                        try:
                                            object[name].append(str(baseToTraverse[name]))
                                        except Exception as e: print(e) 
                                    break
                        elif "objects.geometry." not in baseToTraverse.speckle_type.lower():
                            object = loopObj(sw, object, baseToTraverse[name], attrs)

        return object 
    except: pass


    