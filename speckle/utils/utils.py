import sys
import os
import subprocess

MESSAGE_CATEGORY = "Speckle"


def get_qgis_python_path():
    if sys.platform.startswith("linux"):
        return sys.executable
    pythonExec = os.path.dirname(sys.executable)
    if sys.platform == "win32":
        pythonExec += "\\python3"
    else:
        pythonExec += "/bin/python3"
    return pythonExec
