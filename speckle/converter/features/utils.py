import inspect
import random
from typing import Any
from speckle.converter.layers.utils import getVariantFromValue, traverseDict

from speckle.utils.panel_logging import logToUser

from specklepy.objects import Base


def addFeatVariant(key, variant, value, f: "QgsFeature") -> "QgsFeature":
    try:
        feat = f
        if variant == 10:
            value = str(value)  # string

        if value != "NULL" and value != "None":
            if variant == getVariantFromValue(value):
                feat[key] = value
            elif (
                isinstance(value, float) and variant == 4
            ):  # float, but expecting Long (integer)
                feat[key] = int(value)
            elif (
                isinstance(value, int) and variant == 6
            ):  # int (longlong), but expecting float
                feat[key] = float(value)
            else:
                feat[key] = None
                # print(key); print(value); print(type(value)); print(variant); print(getVariantFromValue(value))
        elif isinstance(variant, int):
            feat[key] = None
        return feat
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return feat


def updateFeat(
    feat: "QgsFeature", fields: "QgsFields", feature: Base
) -> dict[str, Any]:
    try:
        # print("__updateFeat")
        all_field_names = fields.names()
        for i, key in enumerate(all_field_names):
            variant = fields.at(i).type()
            try:
                if key == "Speckle_ID":
                    value = str(feature["id"])
                    # if key != "parameters": print(value)
                    feat[key] = value

                    feat = addFeatVariant(key, variant, value, feat)

                else:
                    try:
                        value = feature[key]
                        feat = addFeatVariant(key, variant, value, feat)

                    except:
                        value = None
                        rootName = key.split("_")[0]
                        # try: # if the root category exists
                        # if its'a list
                        if isinstance(feature[rootName], list):
                            for i in range(len(feature[rootName])):
                                try:
                                    newF, newVals = traverseDict(
                                        {},
                                        {},
                                        rootName + "_" + str(i),
                                        feature[rootName][i],
                                        1,
                                    )
                                    for i, (key, value) in enumerate(newVals.items()):
                                        for k, (x, y) in enumerate(newF.items()):
                                            if key == x:
                                                variant = y
                                                break
                                        feat = addFeatVariant(key, variant, value, feat)
                                except Exception as e:
                                    print(e)
                        # except: # if not a list
                        else:
                            try:
                                newF, newVals = traverseDict(
                                    {}, {}, rootName, feature[rootName], 1
                                )
                                for i, (key, value) in enumerate(newVals.items()):
                                    for k, (x, y) in enumerate(newF.items()):
                                        if key == x:
                                            variant = y
                                            break
                                    feat = addFeatVariant(key, variant, value, feat)
                            except Exception as e:
                                feat.update({key: None})
            except Exception as e:
                feat[key] = None
        # feat_sorted = {k: v for k, v in sorted(feat.items(), key=lambda item: item[0])}
        # print("_________________end of updating a feature_________________________")

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])

    return feat


def getPolygonFeatureHeight(
    feature: "QgsFeature", layer: "QgsVectorLayer", dataStorage: "DataStorage"
):
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
