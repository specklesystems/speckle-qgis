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
    BOOL = "Bool"

    @staticmethod
    def assign_speckle_field_type(native_geom_type: int):

        type_index: int = native_geom_type % 1000
        val_dict = {
            1: GISAttributeFieldType.BOOL,
            2: GISAttributeFieldType.INTEGER_TYPE,
            6: GISAttributeFieldType.DOUBLE_TYPE,
            10: GISAttributeFieldType.STRING_TYPE,
            14: GISAttributeFieldType.DATEONLY,
            15: GISAttributeFieldType.TIMEONLY,
            16: GISAttributeFieldType.DATETIME,
        }
        result: str = val_dict.get(type_index, GISAttributeFieldType.STRING_TYPE)
        return result

    @staticmethod
    def get_native_field_type_from_speckle(string_geom_type: str):

        speckle_type = GISAttributeFieldType(string_geom_type)
        val_dict = {
            GISAttributeFieldType.GUID_TYPE: "Guid",
            GISAttributeFieldType.OID: "Oid",
            GISAttributeFieldType.STRING_TYPE: "String",
            GISAttributeFieldType.FLOAT_TYPE: "Float",
            GISAttributeFieldType.INTEGER_TYPE: "Integer",
            GISAttributeFieldType.BIGINTEGER: "BigInteger",
            GISAttributeFieldType.SMALLINTEGER: "SmallInteger",
            GISAttributeFieldType.DOUBLE_TYPE: "Double",
            GISAttributeFieldType.DATETIME: "DateTime",
            GISAttributeFieldType.DATEONLY: "DateOnly",
            GISAttributeFieldType.TIMEONLY: "TimeOnly",
            GISAttributeFieldType.TIMESTAMPOFFSET: "TimeStampOffset",
            GISAttributeFieldType.BOOL: "Bool",
        }
        result: str = val_dict.get(speckle_type, GISAttributeFieldType.STRING_TYPE)
        return result
