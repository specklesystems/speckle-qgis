
from typing import Any, Callable, List, Optional 

from speckle.logging import logger
from speckle.converter.layers.Layer import VectorLayer, RasterLayer, Layer
from speckle.converter.layers import cadLayerToNative, layerToNative

from specklepy.objects import Base

def traverseObject(
    base: Base,
    callback: Optional[Callable[[Base, str], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
):
    if check and check(base):
        res = callback(base, streamBranch) if callback else False
        if res:
            return
    memberNames = base.get_member_names()
    for name in memberNames:
        try:
            if ["id", "applicationId", "units", "speckle_type"].index(name):
                continue
        except:
            pass
        traverseValue(base[name], callback, check, streamBranch)

def traverseValue(
    value: Any,
    callback: Optional[Callable[[Base, str], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
):
    if isinstance(value, Base):
        traverseObject(value, callback, check, streamBranch)
    if isinstance(value, List):
        for item in value:
            traverseValue(item, callback, check, streamBranch)


def callback(base: Base, streamBranch: str) -> bool:
    if isinstance(base, VectorLayer) or isinstance(base, Layer) or isinstance(base, RasterLayer):
        print(base)
        layer = layerToNative(base, streamBranch)
        if layer is not None:
            logger.log("Layer created: " + layer.name())
    else:
        loopObj(base, "", streamBranch)
    return True

def loopObj(base: Base, baseName: str, streamBranch: str):
    memberNames = base.get_member_names()
    print(baseName)
    for name in memberNames:
        if name in ["id", "applicationId", "units", "speckle_type"]: continue
        try: loopVal(base[name], baseName + "/" + name, streamBranch)
        except: pass

def loopVal(value: Any, name: str, streamBranch: str): # "name" is the parent object/property/layer name
    print(name)
    if isinstance(value, Base): 
        print(value)
        try: # dont go through parts of Speckle Geometry object
            if value.speckle_type.startswith("Objects.Geometry."): pass #.Brep") or value.speckle_type.startswith("Objects.Geometry.Mesh") or value.speckle_type.startswith("Objects.Geometry.Surface") or value.speckle_type.startswith("Objects.Geometry.Extrusion"): pass
            else: loopObj(value, name, streamBranch)
        except: loopObj(value, name, streamBranch)

    if isinstance(value, List):
        print(value)
        for item in value:
            loopVal(item, name, streamBranch)
            if item.speckle_type and item.speckle_type.startswith("Objects.Geometry."): 
                pt, pl = cadLayerToNative(value, name, streamBranch)
                if pt is not None: logger.log("Layer group created: " + str(pt.name()))
                if pl is not None: logger.log("Layer group created: " + str(pl.name()))
                break
