import inspect
from speckle.utils.panel_logging import logToUser


def get_scale_factor(units: str, dataStorage) -> float:
    scale_to_meter = get_scale_factor_to_meter(units)
    if dataStorage is not None:
        scale_back = scale_to_meter / get_scale_factor_to_meter(
            dataStorage.currentUnits
        )
        return scale_back
    else:
        return scale_to_meter


def get_scale_factor_to_meter(units: str) -> float:
    try:
        unit_scale = {
            "meters": 1.0,
            "centimeters": 0.01,
            "millimeters": 0.001,
            "inches": 0.0254,
            "feet": 0.3048,
            "kilometers": 1000.0,
            "mm": 0.001,
            "cm": 0.01,
            "m": 1.0,
            "km": 1000.0,
            "in": 0.0254,
            "ft": 0.3048,
            "yd": 0.9144,
            "mi": 1609.340,
        }
        if (
            units is not None
            and isinstance(units, str)
            and units.lower() in unit_scale.keys()
        ):
            return unit_scale[units]
        logToUser(
            f"Units {units} are not supported. Meters will be applied by default.",
            level=1,
            func=inspect.stack()[0][3],
        )
        return 1.0
    except Exception as e:
        logToUser(
            f"{e}. Meters will be applied by default.",
            level=2,
            func=inspect.stack()[0][3],
        )
        return 1.0
