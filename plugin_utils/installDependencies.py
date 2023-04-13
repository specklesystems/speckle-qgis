import sys
import os.path
import subprocess

from plugin_utils.subprocess_call import subprocess_call
from speckle.logging import logger
from speckle.utils import get_qgis_python_path


def setup():
    # to debug:
    r'''
import os; import sys; import subprocess; pythonExec = os.path.dirname(sys.executable) + "\\python3"
#retcode = subprocess.call([pythonExec, "-m", "pip", "install", "specklepy"]); print(retcode)
result = subprocess.run([pythonExec, "-m", "pip", "install", "specklepy"], capture_output=True, text=True, shell=True, timeout=1000); print(result)
#result = subprocess.run([pythonExec, "-m", "pip", "install", "--upgrade", "specklepy==2.13.0", "-t", target], capture_output=True, text=True, shell=True, timeout=1000); print(result)
            
import specklepy; import os; print(os.path.abspath(specklepy.__file__))


    '''
    plugin_dir = os.path.dirname(__file__)
    pythonExec = get_qgis_python_path() # import specklepy; import os; print(os.path.abspath(specklepy.__file__)) #### import sysconfig; sysconfig.get_paths()['data'] # import qgis; import os; print(os.path.abspath(qgis.__file__)) # C:\Program Files\ArcGIS\Pro\Resources\ArcPy\arcpy\__init__.py

    try:
        import pip
    except:
        logger.log("Pip not installed, setting up now")
        getPipFilePath = os.path.join(plugin_dir, "plugin_utils/get_pip.py")
        exec(open(getPipFilePath).read())

        # just in case the included version is old
        subprocess_call([pythonExec, "-m", "pip", "install", "--upgrade", "pip"])

    pkgVersion = "2.9.0" 
    pkgName = "specklepy"
    try:
        import specklepy
    except Exception as e:
        logger.log("Specklepy not installed")
        subprocess_call(
            [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"]
        )

    # Check if specklpy needs updating
    try:
        logger.log(f"Attempting to update specklepy to {pkgVersion}")
        subprocess_call(
            [
                pythonExec,
                "-m",
                "pip",
                "install",
                "--upgrade",
                f"{pkgName}=={pkgVersion}",
            ]
        )
    except Exception as e:
        logger.log(e.with_traceback)

    #################################################
    pkgVersion = "1.10.11"  # "2.5.3"
    pkgName = "panda3d"
    try:
        import panda3d
    except Exception as e:
        logger.log("panda3d not installed")
        subprocess_call(
            [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"]
        )

    # Check if panda3d needs updating
    try:
        logger.log(f"Attempting to update panda3d to {pkgVersion}")
        subprocess_call(
            [
                pythonExec,
                "-m",
                "pip",
                "install",
                "--upgrade",
                f"{pkgName}=={pkgVersion}",
            ]
        )
    except Exception as e:
        logger.log(e.with_traceback)

    ############################################

    pkgVersion = "66.0"  # "2.5.3"
    pkgName = "cefpython3"
    try:
        from cefpython3 import cefpython as cef
    except Exception as e:
        logger.log("cefpython not installed")
        subprocess_call(
            [pythonExec, "-m", "pip", "install", "--upgrade", f"{pkgName}"]
        )


    ################################################# 
    pkgVersion = "2.3.1"
    pkgName = "pyshp"
    try:
        import shapefile
    except Exception as e:
        logger.log("shapefile not installed")
        subprocess_call(
            [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"]
        )

    # Check if pyshp needs updating
    try:
        logger.log(f"Attempting to update pyshp to {pkgVersion}")
        subprocess_call(
            [
                pythonExec,
                "-m",
                "pip",
                "install",
                "--upgrade",
                f"{pkgName}=={pkgVersion}",
            ]
        )
    except Exception as e:
        logger.log(e.with_traceback)
