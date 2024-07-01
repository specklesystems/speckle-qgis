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
    def assign_speckle_field_type(native_geom_type: int) -> "GISAttributeFieldType":
        """Assign Speckle representation of the Field type."""

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
        result: GISAttributeFieldType = val_dict.get(
            type_index, GISAttributeFieldType.STRING_TYPE
        )
        return result

    @staticmethod
    def get_native_field_type_from_speckle(string_geom_type: str) -> int:
        """Get native Field type (not currently used)."""

        speckle_type = GISAttributeFieldType(string_geom_type)
        val_dict = {
            GISAttributeFieldType.GUID_TYPE: 10,
            GISAttributeFieldType.OID: 10,
            GISAttributeFieldType.STRING_TYPE: 10,
            GISAttributeFieldType.FLOAT_TYPE: 6,
            GISAttributeFieldType.INTEGER_TYPE: 2,
            GISAttributeFieldType.BIGINTEGER: 2,
            GISAttributeFieldType.SMALLINTEGER: 2,
            GISAttributeFieldType.DOUBLE_TYPE: 6,
            GISAttributeFieldType.DATETIME: 16,
            GISAttributeFieldType.DATEONLY: 14,
            GISAttributeFieldType.TIMEONLY: 15,
            GISAttributeFieldType.TIMESTAMPOFFSET: 10,
            GISAttributeFieldType.BOOL: 1,
        }
        result: int = val_dict.get(speckle_type, 10)
        return result
