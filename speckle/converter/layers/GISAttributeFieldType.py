from enum import Enum


class GISAttributeFieldType(str, Enum):
    """GIS VectorLayer geometry types"""

    GUID_TYPE = "Guid"
    OID = "Oid"
    STRING_TYPE = "String"
    FLOAT_TYPE = "Float"
    INTEGER_TYPE = "Integer"
    BIGINTEGER = "BigInteger"
    SMALLINTEGER = "SmallInteger"
    DOUBLE_TYPE = "Double"
    DATETIME = "DateTime"
    DATEONLY = "DateOnly"
    TIMEONLY = "TimeOnly"
    TIMESTAMPOFFSET = "TimeStampOffset"

    r"""
    qgis_types = [
        (1, "bool"), 
        (2, "int"),
        (6, "decimal"),
        (8, "map"),
        (9, "int_list"),
        (10, "string"),
        (11, "string_list"),
        (12, "binary"),
        (14, "date"),
        (15, "time"),
        (16, "date_time") 
    ]
    @staticmethod
    def assign_speckle_layer_geometry_type(native_geom_type: int):

        type_index: int = native_geom_type % 1000
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
        result: str = val_dict.get(type_index, GISLayerGeometryType.NONE)

        # write 3d polygons as a separate type
        if native_geom_type > 1000 and result == GISLayerGeometryType.POLYGON:
            result = GISLayerGeometryType.POLYGON3D

        return result

    @staticmethod
    def get_native_layer_geometry_type_from_speckle(string_geom_type: str):

        speckle_type = GISLayerGeometryType(string_geom_type)
        val_dict = {
            GISLayerGeometryType.NONE: "None",
            GISLayerGeometryType.POINT: "MultiPointZ",
            GISLayerGeometryType.POLYLINE: "MultiLineStringZ",
            GISLayerGeometryType.POLYGON: "MultiPolygon",
            GISLayerGeometryType.POLYGON3D: "MultiPolygonZ",
            GISLayerGeometryType.MULTIPATCH: "MultiPolygonZ",
            # GISLayerGeometryType.POINTCLOUD: ,
        }
        result: str = val_dict.get(speckle_type, "None")
        return result
    """
