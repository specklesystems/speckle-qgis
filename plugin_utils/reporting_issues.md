# Reporting QGIS-Speckle plugin issues

### "Speckle dependencies were not installed."

If restarting QGIS didn't resolve the problem, follow these steps to report the issue and give us more context to help: 

 - Copy and paste this into QGIS Plugins -> Python console. 

```sh

if sys.platform == "win32": pythonExec = os.path.dirname(sys.executable) + "\\python3"
elif sys.platform.startswith("linux"): pythonExec = os.path.dirname(sys.executable)
else: pythonExec = os.path.dirname(sys.executable) + "/bin/python3"

import os; import sys; import subprocess; result = subprocess.run([pythonExec, "-m", "pip", "install", "specklepy==2.14.0"], capture_output=True, text=True, shell=True, timeout=1000); print(result) 

import os; import sys; import subprocess; result = subprocess.run([pythonExec, "-m", "pip", "install", "triangle"], capture_output=True, text=True, shell=True, timeout=1000); print(result) 

import os; import sys; import subprocess; result = subprocess.run([pythonExec, "-m", "pip", "install", "pyshp==2.3.1"], capture_output=True, text=True, shell=True, timeout=1000); print(result) 

```
 - You can choose [Github](https://github.com/specklesystems/speckle-qgis/issues) or [Community Forum](https://speckle.community/) to report the issue. Share a FULL screenshot of the Python console output. Or copy and paste all text from Python console after running the command. You can delete/cover your folder path from the report if needed. 

