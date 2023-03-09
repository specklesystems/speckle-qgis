

from specklepy.objects.geometry import Point, Line, Polyline, Circle, Arc, Polycurve
from specklepy.objects import Base
from typing import List, Union

from speckle.converter.geometry.polyline import speckleArcCircleToPoints, specklePolycurveToPoints


def speckleBoundaryToSpecklePts(boundary: Union[None, Polyline, Arc, Line, Polycurve]) -> List[Point]:
    # add boundary points
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