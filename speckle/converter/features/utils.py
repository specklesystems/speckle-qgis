import inspect
import random

from speckle.utils.panel_logging import logToUser


def getPolygonFeatureHeight(feature, layer, dataStorage):
    height = None
    ignore = False
    if dataStorage.savedTransforms is not None:
        for item in dataStorage.savedTransforms:
            layer_name = item.split("  ->  ")[0].split(" ('")[0]
            transform_name = item.split("  ->  ")[1].lower()
            if "ignore" in transform_name:
                ignore = True

            if layer_name == layer.name():
                attribute = None
                if " ('" in item:
                    attribute = item.split(" ('")[1].split("') ")[0]

                if attribute is None and ignore is False:
                    logToUser(
                        "Attribute for extrusion not selected",
                        level=1,
                        func=inspect.stack()[0][3],
                    )
                    return None

                # print("Apply transform: " + transform_name)
                if "extrude" in transform_name and "polygon" in transform_name:
                    # additional check:
                    try:
                        if dataStorage.project.crs().isGeographic():
                            return None
                    except:
                        return None

                    try:
                        existing_height = float(feature[attribute])
                        if (
                            existing_height is None or str(feature[attribute]) == "NULL"
                        ):  # if attribute value invalid
                            if ignore is True:
                                return None
                            else:  # find approximate value
                                all_existing_vals = [
                                    f[attribute]
                                    for f in layer.getFeatures()
                                    if (
                                        f[attribute] is not None
                                        and (
                                            isinstance(f[attribute], float)
                                            or isinstance(f[attribute], int)
                                        )
                                    )
                                ]
                                try:
                                    if len(all_existing_vals) > 5:
                                        height_average = all_existing_vals[
                                            int(len(all_existing_vals) / 2)
                                        ]
                                        height = random.randint(
                                            height_average - 5, height_average + 5
                                        )
                                    else:
                                        height = random.randint(10, 20)
                                except:
                                    height = random.randint(10, 20)
                        else:  # if acceptable value: reading from existing attribute
                            height = existing_height

                    except:  # if no Height attribute
                        if ignore is True:
                            height = None
                        else:
                            height = random.randint(10, 20)

    return height
