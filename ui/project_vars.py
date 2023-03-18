

# Persist added streams in project
import inspect
import time
from speckle.converter.layers.utils import saveCRS
from speckle_qgis import SpeckleQGIS

from specklepy.logging.exceptions import SpeckleException 
from specklepy.api.wrapper import StreamWrapper
from specklepy.logging import metrics

from speckle.logging import logger
from qgis.core import (Qgis, QgsProject, QgsCoordinateReferenceSystem)
from ui.logger import logToUser
from ui.validation import tryGetStream

def get_project_streams(plugin: SpeckleQGIS):
    try:
        proj = plugin.qgis_project
        saved_streams = proj.readEntry("speckle-qgis", "project_streams", "")
        temp = []
        ######### need to check whether saved streams are available (account reachable)
        if saved_streams[1] and len(saved_streams[0]) != 0:
            
            for url in saved_streams[0].split(","):
                try:
                    sw = StreamWrapper(url)
                    try: 
                        stream = tryGetStream(sw)
                    except SpeckleException as e:
                        logToUser(e.message, level = 1, func = inspect.stack()[0][3])
                        stream = None
                    #strId = stream.id # will cause exception if invalid
                    temp.append((sw, stream))
                except SpeckleException as e:
                    logToUser(e.message, level = 1, func = inspect.stack()[0][3])
                #except GraphQLException as e:
                #    logger.logToUser(e.message, Qgis.Warning)
        plugin.current_streams = temp
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return
    
def set_project_streams(plugin: SpeckleQGIS):
    try:
        proj = plugin.qgis_project
        value = ",".join([stream[0].stream_url for stream in plugin.current_streams])
        proj.writeEntry("speckle-qgis", "project_streams", value)
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return
  
def get_project_layer_selection(plugin: SpeckleQGIS):
    try:
        proj = plugin.qgis_project
        saved_layers = proj.readEntry("speckle-qgis", "project_layer_selection", "")
        temp = []
        ######### need to check whether saved streams are available (account reachable)
        if saved_layers[1] and len(saved_layers[0]) != 0:
            
            for id in saved_layers[0].split(","):
                found = 0
                for layer in proj.mapLayers().values():
                    if layer.id() == id:
                        temp.append((layer.name(), layer))
                        found += 1
                        break
                if found == 0: 
                    logToUser(f'Saved layer not found: "{id}"', level = 1, func = inspect.stack()[0][3])
        plugin.current_layers = temp
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return

def set_project_layer_selection(plugin: SpeckleQGIS):
    try:
        proj = plugin.qgis_project
        #value = ",".join([x.id() for x in self.iface.layerTreeView().selectedLayers()]) #'points_qgis2_b22ed3d0_0ff9_40d2_97f2_bd17a350d698' <qgis._core.QgsVectorDataProvider object at 0x000002627D9D4790>
        value = ",".join([x[1].id() for x in plugin.current_layers]) 
        proj.writeEntry("speckle-qgis", "project_layer_selection", value)
        metrics.track("Connector Action", plugin.active_account, {"name": "Toggle Set layer selection"})

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return
    
def get_survey_point(plugin: SpeckleQGIS):
    try:
        # get from saved project, set to local vars
        proj = plugin.qgis_project
        points = proj.readEntry("speckle-qgis", "survey_point", "")
        if points[1] and len(points[0])>0: 
            vals: list[str] = points[0].replace(" ","").split(";")[:2]
            plugin.lat, plugin.lon = [float(i) for i in vals]
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return
    
def set_survey_point(plugin: SpeckleQGIS):
    try: 
        # from widget (3 strings) to local vars AND memory (1 string)
        proj = plugin.qgis_project
        vals =[ str(plugin.dockwidget.surveyPointLat.text()), str(plugin.dockwidget.surveyPointLon.text()) ]

        plugin.lat, plugin.lon = [float(i.replace(" ","")) for i in vals]
        pt = str(plugin.lat) + ";" + str(plugin.lon) 
        proj.writeEntry("speckle-qgis", "survey_point", pt)
        setProjectReferenceSystem(plugin)
        metrics.track("Connector Action", plugin.active_account, {"name": "Toggle Set survey point"})
        return True
    
    except Exception as e:
        logToUser("Lat, Lon values invalid: " + str(e), level = 2, plugin=plugin.dockwidget)
        return False 
    
def setProjectReferenceSystem(plugin: SpeckleQGIS):
    # Create CRS and apply to the project:
    # https://gis.stackexchange.com/questions/379199/having-problem-with-proj-string-for-custom-coordinate-system
    # https://proj.org/usage/projections.html
    try: 
        newCrsString = "+proj=tmerc +ellps=WGS84 +datum=WGS84 +units=m +no_defs +lon_0=" + str(plugin.lon) + " lat_0=" + str(plugin.lat) + " +x_0=0 +y_0=0 +k_0=1"
        newCrs = QgsCoordinateReferenceSystem().fromProj(newCrsString)#fromWkt(newProjWkt)
        validate = QgsCoordinateReferenceSystem().createFromProj(newCrsString)

        if validate: 
            authid = saveCRS(newCrs, "latlon_"+str(plugin.lat)+"_"+str(plugin.lon))

            newID = int(authid.replace("USER:",""))
            crs = QgsCoordinateReferenceSystem().fromSrsId(newID)
            plugin.qgis_project.setCrs(crs) 
            #listCrs = QgsCoordinateReferenceSystem().validSrsIds()
            #if exists == 0: newCrs.saveAsUserCrs("SpeckleCRS_lon=" + str(sPoint.x()) + "_lat=" + str(sPoint.y())) # srsid() #https://gis.stackexchange.com/questions/341500/creating-custom-crs-in-qgis
            logToUser("Custom project CRS successfully applied", level = 0, plugin=plugin.dockwidget)
        else:
            logToUser("Custom CRS could not be created", level = 1, plugin=plugin.dockwidget)
    except:
        logToUser("Custom CRS could not be created", level = 1, plugin=plugin.dockwidget)
    
    return True
