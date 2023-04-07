

import inspect
import random
from specklepy.objects.geometry import Point, Line, Polyline, Circle, Arc, Polycurve
from specklepy.objects import Base
from typing import List, Union

from speckle.converter.geometry.polyline import speckleArcCircleToPoints, specklePolycurveToPoints
from ui.logger import logToUser

def fix_orientation(polyBorder: List, positive = True, coef = 1): 
    sum_orientation = 0 
    for k, ptt in enumerate(polyBorder): #pointList:
        try: 
            pt = polyBorder[k*coef]
            pt2 = polyBorder[(k+1)*coef]
            sum_orientation += (pt2.x - pt.x) * (pt2.y + pt.y)
        except: break
    if positive is True: 
        if sum_orientation < 0:
            polyBorder.reverse()
    else: 
        if sum_orientation > 0:
            polyBorder.reverse()
    
    return polyBorder
    
def getPolygonFeatureHeight(feature, layer):
    
    try:
        existing_height = feature["height"]
        if existing_height is None or str(existing_height) == "NULL": # if attribute value invalid
            #height = random.randint(10, 20)
            all_existing_vals = [f["height"] for f in layer.getFeatures() if (f["height"] is not None and (isinstance(f["height"], float) or isinstance(f["height"], int) ) ) ]
            try: 
                if len(all_existing_vals) > 5:
                    height_average = all_existing_vals[int(len(all_existing_vals)/2)]
                    height = random.randint(height_average-5, height_average+5)
                else:
                    height = random.randint(10, 20)
            except: 
                height = random.randint(10, 20)
        else: # reading from existing attribute 
            height = existing_height
    except: # if no Height attribute
        height = random.randint(10, 20)
        
    return height


def speckleBoundaryToSpecklePts(boundary: Union[None, Polyline, Arc, Line, Polycurve]) -> List[Point]:
    # add boundary points
    try:
        polyBorder = []
        if isinstance(boundary, Circle) or isinstance(boundary, Arc): 
            polyBorder = speckleArcCircleToPoints(boundary) 
        elif isinstance(boundary, Polycurve): 
            polyBorder = specklePolycurveToPoints(boundary) 
        elif isinstance(boundary, Line): pass
        else: 
            try: polyBorder = boundary.as_points()
            except: pass # if Line or None
        return polyBorder
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    