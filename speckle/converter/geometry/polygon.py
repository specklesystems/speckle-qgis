""" This module contains all geometry conversion functionality To and From Speckle."""

from qgis.core import (
    Qgis, QgsPolygon, QgsFeature, QgsVectorLayer
)
from typing import Sequence

from specklepy.objects import Base

from speckle.converter.geometry.mesh import rasterToMesh
from speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    polylineToNative,
)
from speckle.logging import logger
import math


def polygonToSpeckle(geom: QgsPolygon, feature: QgsFeature, layer: QgsVectorLayer):
    """Converts a QgsPolygon to Speckle"""
    try: 
      #print(geom)
      polygon = Base()
      boundary = polylineFromVerticesToSpeckle(
          geom.exteriorRing().vertices(), True
      )
      #print(boundary)
      
      voids = []
      for i in range(geom.numInteriorRings()):
          intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True)
          voids.append(intRing)
      polygon.boundary = boundary
      polygon.voids = voids
      #print(voids)
      polygon.displayValue = [ boundary ] + voids
      if len(voids) == 0: 
        # QgsLineString - LineStringZ
        vertices = []
        qgisVertices = []
        for pt in geom.exteriorRing().vertices():
          x = pt.x()
          y = pt.y()
          z = 0 if math.isnan(pt.z()) else pt.z() # when unset, z() returns "nan"
          vertices.extend([x,y,z])
          qgisVertices.append(pt)

        ran = range(0, len(qgisVertices))
        faces = [len(qgisVertices)]
        faces.extend([i for i in ran])
        #print(layer.renderer().type())

        # case with one color for the entire layer
        if layer.renderer().type() == 'categorizedSymbol' or layer.renderer().type() == '25dRenderer' or layer.renderer().type() == 'invertedPolygonRenderer' or layer.renderer().type() == 'mergedFeatureRenderer' or layer.renderer().type() == 'RuleRenderer' or layer.renderer().type() == 'nullSymbol' or layer.renderer().type() == 'singleSymbol' or layer.renderer().type() == 'graduatedSymbol':
          #get color value
          if layer.renderer().type() == 'singleSymbol':
            color = layer.renderer().symbol().color()
          elif layer.renderer().type() == 'categorizedSymbol':
            category = layer.renderer().legendClassificationAttribute() # get the name of attribute used for classification
            for obj in layer.renderer().categories():
              if obj.value() == feature.attribute( category ): 
                color = obj.symbol().color()
                break
          # construct RGB color
          try:
            rVal = color.red()
            gVal = color.green()
            bVal = color.blue()
          except:
            rVal = 0
            gVal = 0
            bVal = 0
          col =  (rVal<<16) + (gVal<<8) + bVal
          colors = [col for i in ran] 
        mesh = rasterToMesh(vertices, faces, colors)
        #polygon.displayValue = mesh 
      return polygon
    except: 
      logger.logToUser("Some polygons might be invalid", Qgis.Warning)
      pass


def polygonToNative(poly: Base) -> QgsPolygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""
    print(polylineToNative(poly["boundary"]))
    
    polygon = QgsPolygon()
    polygon.setExteriorRing(polylineToNative(poly["boundary"]))
    try:
      for void in poly["voids"]: 
        print(polylineToNative(void))
        polygon.addInteriorRing(polylineToNative(void))
    except:
      pass
    print(polygon)
    print()

    #polygon = QgsPolygon(
    #    polylineToNative(poly["boundary"]),
    #    [polylineToNative(void) for void in poly["voids"]],
    #)
    return polygon
