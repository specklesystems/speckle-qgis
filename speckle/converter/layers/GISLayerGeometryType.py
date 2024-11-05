from enum import Enum
from typing import Optional


class GISLayerGeometryType(str, Enum):
    """GIS VectorLayer geometry types"""

    NONE = "None"
    POINT = "Point"
    POLYLINE = "Polyline"
    POLYGON = "Polygon"
    POLYGON3D = "Polygon3d"
    MULTIPATCH = "Multipatch"
    POINTCLOUD = "Pointcloud"

    @staticmethod
    def assign_speckle_layer_geometry_type(
        native_geom_type: int,
    ) -> "GISLayerGeometryType":
        """Get Speckle representation of the Layer Geometry Type."""

        type_index: int = native_geom_type % 1000  # e.g.3004->7, 4002->4
        val_dict = {
            1: GISLayerGeometryType.POINT,
            2: GISLayerGeometryType.POLYLINE,
            3: GISLayerGeometryType.POLYGON,
            4: GISLayerGeometryType.POINT,
            5: GISLayerGeometryType.POLYLINE,
            6: GISLayerGeometryType.POLYGON,
            7: "GeometryCollection",
            8: GISLayerGeometryType.POLYLINE,
            9: GISLayerGeometryType.POLYLINE,
            10: GISLayerGeometryType.POLYGON,
            11: GISLayerGeometryType.POLYLINE,
            12: "MultiSurface",
            17: "Triangle",
        }
        result: GISLayerGeometryType = val_dict.get(
            type_index, GISLayerGeometryType.NONE
        )

        # write 3d polygons as a separate type
        # geometry types of 1,2,3 etc (<1000) have 2 dimensions, rest: 3
        if native_geom_type > 1000 and result == GISLayerGeometryType.POLYGON:
            result = GISLayerGeometryType.POLYGON3D

        return result

    @staticmethod
    def get_native_layer_geometry_type_from_speckle(
        geom_type: str,
    ) -> Optional[str]:
        """Get native Layer Geometry Type."""

        val_dict = {
            GISLayerGeometryType.NONE: "None",
            GISLayerGeometryType.POINT: "MultiPointZ",
            GISLayerGeometryType.POLYLINE: "MultiLineStringZ",
            GISLayerGeometryType.POLYGON: "MultiPolygon",
            GISLayerGeometryType.POLYGON3D: "MultiPolygonZ",
            GISLayerGeometryType.MULTIPATCH: "MultiPolygonZ",
            # GISLayerGeometryType.POINTCLOUD: ,
        }
        
        try:
            speckle_geom_type = GISLayerGeometryType(geom_type)
            result: Optional[str] = val_dict.get(speckle_geom_type)
        except:
            # for older commits
            if "point" in geom_type.lower():
                result = "MultiPointZ"
            elif "line" in geom_type.lower():
                result = "MultiLineStringZ"
            elif (
                "polygon" in geom_type.lower()
                or "multipatch" in geom_type.lower()
            ):
                result = "MultiPolygonZ"

        return result
