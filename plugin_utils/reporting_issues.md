# Reporting QGIS-Speckle plugin issues

### "Speckle dependencies were not installed."

If restarting QGIS didn't resolve the problem, follow these steps to report the issue and give us more context to help: 

You can run the 2 following commands from QGIS Plugins panel->Python Console, and then restart QGIS:

```
def upgradeDependencies():
    import subprocess
    from speckle.utils.utils import get_qgis_python_path as path
    result = subprocess.run([path(), "-m", "pip", "install", "requests==2.31.0"],shell=True,timeout=1000,)
    print(result.returncode)
    result = subprocess.run([path(), "-m", "pip", "install", "urllib3==1.26.16"],shell=True,timeout=1000,)
    print(result.returncode)
    result = subprocess.run([path(), "-m", "pip", "install", "requests_toolbelt==0.10.1"],shell=True,timeout=1000,)
    print(result.returncode)

upgradeDependencies()
```
You can choose [Github](https://github.com/specklesystems/speckle-qgis/issues) or [Community Forum](https://speckle.community/) to report the issue. 

