import sys
import os.path
import subprocess
from .speckle.logging import logger
from .speckle.utils import get_qgis_python_path


def setup():
    plugin_dir = os.path.dirname(__file__)
    pythonExec = get_qgis_python_path()

    try:
        import pip
    except:
        logger.log("Pip not installed, setting up now")
        getPipFilePath = os.path.join(plugin_dir, "get_pip.py")
        exec(open(getPipFilePath).read())

        # just in case the included version is old
        subprocess.call(
            [pythonExec, '-m', 'pip', 'install', '--upgrade', 'pip'])

    pkgVersion = "2.3.5"
    pkgName = 'specklepy'
    try:
        import specklepy
        print(str(specklepy))
    except Exception as e:
        logger.log("Specklepy not installed")
        subprocess.call([pythonExec, '-m', 'pip', 'install',
                        f"{pkgName}=={pkgVersion}"])
    
    # Check if specklpy needs updating
    try:
        from importlib_metadata import version
        current = version(pkgName)
        if(current != pkgVersion):
            subprocess.call([pythonExec, '-m', 'pip', 'install', '--upgrade',
                        f"{pkgName}=={pkgVersion}"])
    except Exception as e:
        logger.logToUser("Error updating specklepy")