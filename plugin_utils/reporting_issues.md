# Reporting QGIS-Speckle plugin issues

### "Speckle dependencies were not installed."

To resolve dependencies manually, make sure you have the following versions on libraries installed as a primary source for QGIS (e.g. AppData>Roaming>Python or ProgramFiles>QGIS>apps>Python):
- requests==2.31.0
- urllib3==1.26.16
- requests_toolbelt==0.10.0
You can run the 2 following commands from QGIS Plugins panel->Python Console, and then restart QGIS:

```
def upgradeDependencies():
    import subprocess
    from speckle.utils.utils import get_qgis_python_path as path
    result = subprocess.run([path(), "-m", "pip", "install", "requests==2.31.0"],shell=True,timeout=1000,)
    print(result.returncode)
    result = subprocess.run([path(), "-m", "pip", "install", "urllib3==1.26.16"],shell=True,timeout=1000,)
    print(result.returncode)
    result = subprocess.run([path(), "-m", "pip", "install", "requests_toolbelt==0.10.0"],shell=True,timeout=1000,)
    print(result.returncode)

upgradeDependencies()
```
You can choose [Github](https://github.com/specklesystems/speckle-qgis/issues) or [Community Forum](https://speckle.community/) to report the issue. 

