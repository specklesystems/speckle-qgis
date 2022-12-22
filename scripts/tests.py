
# https://towardsdatascience.com/how-to-use-qgis-spatial-algorithms-with-python-scripts-4bf980e39898#:~:text=You%20can't%20import%20the,find%20the%20QGIS%20library%20paths.
# necessary imports
import os
import sys
import json
import subprocess
import sys

IS_WIN32 = 'win32' in str(sys.platform).lower()

def subprocess_call(*args, **kwargs):
    #also works for Popen. It creates a new *hidden* window, so it will work in frozen apps (.exe).
    if IS_WIN32:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
    retcode = subprocess.call(*args, **kwargs)
    print(retcode)
    return retcode

try: import pandas as pd
except: 
    print(sys.executable)
    pythonExec = sys.executable
    subprocess_call([pythonExec, "-m", "pip", "install", "pandas"])
    import pandas as pd

# set up system paths
qspath = os.path.abspath(__file__).replace('tests.py','qgis_sys_paths.csv' ) 
# provide the path where you saved this file.
paths = pd.read_csv(qspath).paths.tolist()
sys.path += paths
# set up environment variables
qepath = os.path.abspath(__file__).replace('tests.py', 'qgis_env.json') 
js = json.loads(open(qepath, 'r').read())
for k, v in js.items():
    os.environ[k] = v
    print( k + ":  " + v)

# qgis library imports
import PyQt5.QtCore
import gdal
import qgis.PyQt.QtCore
from qgis.core import (QgsApplication,
                       QgsProcessingFeedback,
                       QgsProcessingRegistry)
from qgis.analysis import QgsNativeAlgorithms


from qgis.core import *

# Supply path to qgis install location
QgsApplication.setPrefixPath("/path/to/qgis/installation", True)

# Create a reference to the QgsApplication.  Setting the
# second argument to False disables the GUI.
qgs = QgsApplication([], False)

# Load providers
qgs.initQgis()

# Write your code here to load some layers, use processing
# algorithms, etc.

# Finally, exitQgis() is called to remove the
# provider and layer registries from memory
qgs.exitQgis()

