import sys
import os
import traceback
import subprocess
from qgis.core import QgsMessageLog, Qgis

from speckle.utils.panel_logging import logger

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


def enable_remote_debugging():
    try:
        import ptvsd
    except:
        r'''
        QgsMessageLog.logMessage(
            "PTVSD not installed, setting up now", MESSAGE_CATEGORY, Qgis.Info
        )
        '''
        subprocess.call([get_qgis_python_path(), "-m", "pip", "install", "ptvsd"])
    try:
        import ptvsd

        if ptvsd.is_attached():
            r'''
            QgsMessageLog.logMessage(
                "Remote Debug for Visual Studio is already active",
                MESSAGE_CATEGORY,
                Qgis.Info,
            )
            '''
            return
        ptvsd.enable_attach(address=("localhost", 5678))

        # Enable this if you want to be able to hit early breakpoints. Execution will stop until IDE attaches to the port, but QGIS will appear to be unresponsive!!!!
        # ptvsd.wait_for_attach()
        r'''
        QgsMessageLog.logMessage(
            "Attached remote Debug for Visual Studio", MESSAGE_CATEGORY, Qgis.Success
        )
        '''
    except Exception as e:
        r'''
        QgsMessageLog.logMessage(
            "Failed to attach to PTVSD", MESSAGE_CATEGORY, Qgis.Info
        )
        '''
