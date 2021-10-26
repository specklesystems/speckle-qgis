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

    try:
        import specklepy
    except Exception as e:
        logger.log("Specklepy not installed")

        version = "2.3.5"
        package = 'specklepy'
        subprocess.call([pythonExec, '-m', 'pip', 'install',
                        f"{package}=={version}"])
