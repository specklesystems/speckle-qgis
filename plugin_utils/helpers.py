import os
from typing import List
from textwrap import wrap

import inspect
from difflib import SequenceMatcher

from specklepy.objects.units import get_units_from_string

SYMBOL = "_x_x_"
UNSUPPORTED_PROVIDERS = ["WFS", "wms", "wcs", "vectortile"]


def string_diff(string1: str, string2: str) -> str:

    match = SequenceMatcher(None, string1, string2).find_longest_match(
        0, len(string1), 0, len(string2)
    )
    diff = f"\n{string1[: match.a]} [...] {string1[match.a + match.size :]}"
    diff += f"\n{string2[: match.b]} [...] {string2[match.b + match.size :]}"

    return diff


def get_scale_factor(units: str, dataStorage) -> float:
    scale_to_meter = get_scale_factor_to_meter(units)
    if dataStorage is not None:
        scale_back = scale_to_meter / get_scale_factor_to_meter(
            dataStorage.currentUnits
        )
        return scale_back
    else:
        return scale_to_meter


def get_scale_factor_to_meter(units_src: str) -> float:
    units = str(get_units_from_string(units_src))
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
        try:
            from speckle.utils.panel_logging import logToUser

            logToUser(
                f"Units {units_src} are not supported. Meters will be applied by default.",
                level=1,
                func=inspect.stack()[0][3],
            )
            return 1.0
        except:
            print(
                f"Units {units_src} are not supported. Meters will be applied by default."
            )
            return 1.0
    except Exception as e:
        try:
            from speckle.utils.panel_logging import logToUser

            logToUser(
                f"{e}. Meters will be applied by default.",
                level=2,
                func=inspect.stack()[0][3],
            )
            return 1.0
        except:
            print(f"{e}. Meters will be applied by default.")
            return 1.0


def jsonFromList(jsonObj: dict, levels: list):
    # print("jsonFromList")
    if len(levels) == 0:
        return jsonObj
    lastLevel = jsonObj
    for l in levels:
        # print(lastLevel)
        try:
            lastLevel = lastLevel[l]
        except:
            lastLevel.update({l: {}})
    # print(jsonObj)
    return jsonObj


def constructCommitURL(
    streamWrapper, branch_id: str = None, commit_id: str = None
) -> str:
    import requests

    streamUrl = streamWrapper.stream_url.split("?")[0].split("&")[0].split("@")[0]
    r = requests.get(streamUrl)

    url = streamUrl
    # check for frontend2
    try:
        header = r.headers["x-speckle-frontend-2"]
        url = (
            streamUrl.replace("streams", "projects")
            + "/models/"
            + branch_id
            + "@"
            + commit_id
        )
    except:
        url = streamUrl.replace("projects", "streams") + "/commits/" + commit_id
    return url


def getAppName(name: str) -> str:
    new_name = ""
    for i, x in enumerate(str(name)):
        if x.lower() in [a for k, a in enumerate("abcdefghijklmnopqrstuvwxyz")]:
            new_name += x
        else:
            break
    return new_name


def findOrCreatePath(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def removeSpecialCharacters(text: str) -> str:
    new_text = (
        text.replace("<", "_")
        .replace(">", "_")
        .replace("[", "_")
        .replace("]", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "_")
        .replace(")", "_")
        .replace(":", "_")
        .replace("\\", "_")
        .replace("/", "_")
        .replace("|", "_")
        .replace('"', "_")
        .replace("'", "_")
        .replace("&", "_")
        .replace("@", "_")
        .replace("$", "_")
        .replace("%", "_")
        .replace("^", "_")
        .replace(",", "_")
        .replace(".", "_")
    )
    new_text = (
        new_text.replace("_____", "_")
        .replace("____", "_")
        .replace("___", "_")
        .replace("__", "_")
    )
    return new_text


def splitTextIntoLines(text: str = "", number: int = 40) -> str:
    # print("__splitTextIntoLines")
    # print(text)
    msg = ""
    try:
        if len(text) > number:
            try:
                lines = wrap(text, number)
                for i, x in enumerate(lines):
                    msg += x
                    if i != len(lines) - 1:
                        msg += "\n"
            except Exception as e:
                print(e)
        else:
            msg = text
    except Exception as e:
        print(e)
        # print(text)
    return msg


def findFeatColors(fetColors: List, f):
    colorFound = 0
    try:  # get render material from any part of the mesh (list of items in displayValue)
        for k, item in enumerate(f.displayValue):
            try:
                fetColors.append(item.renderMaterial.diffuse)
                colorFound += 1
                break
            except:
                pass
        if colorFound == 0:
            fetColors.append(f.renderMaterial.diffuse)
    except:  # if no "DisplayValue"
        try:
            for k, item in enumerate(f["@displayValue"]):
                try:
                    fetColors.append(item.renderMaterial.diffuse)
                    colorFound += 1
                    break
                except:
                    pass
            if colorFound == 0:
                fetColors.append(f.renderMaterial.diffuse)
        except:
            # the Mesh itself has a renderer
            try:  # get render material from any part of the mesh (list of items in displayValue)
                fetColors.append(f.renderMaterial.diffuse)
                colorFound += 1
            except:
                try:
                    fetColors.append(f.displayStyle.color)
                    colorFound += 1
                except:
                    try:  # if all vertices colors are the same, apply it
                        sameColors = True
                        color1 = f.colors[0]
                        for c in f.colors:
                            if c != color1:
                                sameColors = False
                                break
                        if sameColors is True:
                            fetColors.append(f.colors[0])
                            colorFound += 1
                    except:
                        pass
    if colorFound == 0:
        fetColors.append(None)
    return fetColors
