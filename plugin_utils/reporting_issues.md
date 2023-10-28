# Reporting QGIS-Speckle plugin issues

### "Speckle dependencies were not installed."

To resolve dependencies manually, make sure you have the following versions on libraries installed as a primary source for QGIS (e.g. AppData>Roaming>Python or ProgramFiles>QGIS>apps>Python):
- requests==2.31.0
- urllib3==1.26.16
- requests_toolbelt==0.10.0

You can run the following command from QGIS Plugins panel->Python Console, and then restart QGIS:

```
import os, sys
def get_qgis_python_path():
    if sys.platform.startswith("linux"):
        return sys.executable
    pythonExec = os.path.dirname(sys.executable)
    if sys.platform == "win32":
        pythonExec += "\\python3"
    else:
        pythonExec += "/bin/python3"
    return pythonExec

def upgradeDependencies():
    import subprocess
    result = subprocess.run([get_qgis_python_path(), "-m", "pip", "install", "requests==2.31.0"],shell=True,timeout=1000,)
    print(result.returncode)
    result = subprocess.run([get_qgis_python_path(), "-m", "pip", "install", "urllib3==1.26.16"],shell=True,timeout=1000,)
    print(result.returncode)
    result = subprocess.run([get_qgis_python_path(), "-m", "pip", "install", "requests_toolbelt==0.10.1"],shell=True,timeout=1000,)
    print(result.returncode)

upgradeDependencies()
```
You can choose [Github](https://github.com/specklesystems/speckle-qgis/issues) or [Community Forum](https://speckle.community/) to report the issue. 

