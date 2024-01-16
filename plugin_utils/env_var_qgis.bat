$Env:Pythonpath = ";" + $Env:OSGEO4W_ROOT + "\apps\qgis\python"
setx PYTHONPATH "$Env:Pythonpath"

$Env:OSGEO4W_ROOT = "C:\OSGeo4W64"
$Env:Path = $Env:OSGEO4W_ROOT + "\apps\qgis\bin;" + $Env:Path
setx PATH "$Env:Path"
