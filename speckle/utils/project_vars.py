

# Persist added streams in project
import inspect
import time
from typing import List
from speckle.converter.layers.utils import getElevationLayer, trySaveCRS
from speckle_qgis import SpeckleQGIS

from specklepy.logging.exceptions import SpeckleException 
from specklepy.core.api.wrapper import StreamWrapper
from specklepy.core.api.models import Stream
from specklepy.logging import metrics
from specklepy.core.api.client import SpeckleClient

#from speckle.utils.panel_logging import logger
from qgis.core import (Qgis, QgsProject, QgsCoordinateReferenceSystem)
from specklepy_qt_ui.qt_ui.DataStorage import DataStorage
from specklepy_qt_ui.qt_ui.logger import displayUserMsg, logToUser
from speckle.utils.validation import tryGetStream
from specklepy_qt_ui.qt_ui.widget_custom_crs import CustomCRSDialog

def get_project_streams(plugin: SpeckleQGIS):
    try:
        proj = plugin.project
        saved_streams = proj.readEntry("speckle-qgis", "project_streams", "")
        temp = []
        ######### need to check whether saved streams are available (account reachable)
        if saved_streams[1] and len(saved_streams[0]) != 0:
            
            for url in saved_streams[0].split(","):
                try:
                    sw = StreamWrapper(url)
                    try: 
                        plugin.dataStorage.check_for_accounts()
                        stream = tryGetStream(sw, plugin.dataStorage, False, plugin.dockwidget)
                    except Exception as e:
                        logToUser(e, level = 1, func = inspect.stack()[0][3])
                        stream = None
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
        proj = plugin.project
        value = ",".join([stream[0].stream_url for stream in plugin.current_streams])
        proj.writeEntry("speckle-qgis", "project_streams", value)
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return
  
def get_project_saved_layers(plugin: SpeckleQGIS):
    try:
        proj = plugin.project
        saved_layers = proj.readEntry("speckle-qgis", "project_layer_selection", "")
        temp = []
        #print(saved_layers)
        if saved_layers[1] and len(saved_layers[0]) != 0:
            
            for id in saved_layers[0].split(","):
                found = 0
                for layer in proj.mapLayers().values():
                    if layer.id() == id:
                        temp.append((layer, layer.name(), ""))
                        found += 1
                        break
                if found == 0: 
                    logToUser(f'Saved layer not found: "{id}"', level = 1, func = inspect.stack()[0][3])
        plugin.dataStorage.current_layers = temp.copy()
        plugin.dataStorage.saved_layers = temp.copy()
        #print(temp)
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return

def set_project_layer_selection(plugin: SpeckleQGIS):
    try:
        proj = plugin.project
        #value = ",".join([x.id() for x in self.iface.layerTreeView().selectedLayers()]) #'points_qgis2_b22ed3d0_0ff9_40d2_97f2_bd17a350d698' <qgis._core.QgsVectorDataProvider object at 0x000002627D9D4790>
        value = ",".join([x[0].id() for x in plugin.dataStorage.current_layers]) 
        
        #print(value)
        proj.writeEntry("speckle-qgis", "project_layer_selection", value)
        try: metrics.track("Connector Action", plugin.dataStorage.active_account, {"name": "Save Layer Selection", "connector_version": str(plugin.dataStorage.plugin_version)})
        except Exception as e: logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget )

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget)
        return
     
def get_rotation(dataStorage: DataStorage):
    try:
        # get from saved project, set to local vars
        proj = dataStorage.project
        points = proj.readEntry("speckle-qgis", "crs_rotation", "")
        if points[1] and len(points[0])>0: 
            vals: List[str] = points[0].replace(" ","").split(";")[0]
            dataStorage.crs_rotation = float(vals)
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
def set_rotation(dataStorage: DataStorage, dockwidget = None):
    try: 
        # from widget (3 strings) to local vars AND memory (1 string)
        proj = dataStorage.project
        r = dataStorage.crs_rotation
        if dataStorage.crs_rotation is None:
            r = 0
        proj.writeEntry("speckle-qgis", "crs_rotation", r)
        return True
    
    except Exception as e:
        logToUser("Lat, Lon values invalid: " + str(e), level = 2)
        return False 
    
def get_survey_point(dataStorage: DataStorage):
    try:
        # get from saved project, set to local vars
        proj = dataStorage.project
        points = proj.readEntry("speckle-qgis", "survey_point", "")
        if points[1] and len(points[0])>0: 
            #print(points[0])
            vals: List[str] = points[0].replace(" ","").split(";")[:2]
            dataStorage.custom_lat, dataStorage.custom_lon = [float(i) for i in vals]
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
def set_survey_point(dataStorage: DataStorage, dockwidget = None):
    try: 
        # from widget (3 strings) to local vars AND memory (1 string)
        proj = dataStorage.project
        x = dataStorage.custom_lat
        y = dataStorage.custom_lon

        if dataStorage.custom_lat is None or dataStorage.custom_lon is None: 
            x = 0
            y = 0
        pt = str(x) + ";" + str(y) 
        proj.writeEntry("speckle-qgis", "survey_point", pt)
        
        #try:
        #    metrics.track("Connector Action", dataStorage.active_account, {"name": "Set As Center Point", "connector_version": str(dataStorage.plugin_version)})
        #except Exception as e:
        #    logToUser(e, level = 2, func = inspect.stack()[0][3] )
        return True
    
    except Exception as e:
        logToUser("Lat, Lon values invalid: " + str(e), level = 2)
        return False 

def get_crs_offsets(dataStorage: DataStorage):
    try:
        # get from saved project, set to local vars
        proj = dataStorage.project
        points = proj.readEntry("speckle-qgis", "crs_offsets_rotation", "")
        if points[1] and len(points[0])>0: 
            vals: List[str] = points[0].replace(" ","").split(";")[:2]
            dataStorage.crs_offset_x, dataStorage.crs_offset_y = [float(i) for i in vals]
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
def set_crs_offsets(dataStorage: DataStorage, dockwidget = None):
    try: 
        # from widget (3 strings) to local vars AND memory (1 string)
        proj = dataStorage.project
        x = dataStorage.crs_offset_x
        y = dataStorage.crs_offset_y

        if dataStorage.crs_offset_x is None or dataStorage.crs_offset_y is None: 
            x = 0
            y = 0
        pt = str(x) + ";" + str(y)
        proj.writeEntry("speckle-qgis", "crs_offsets_rotation", pt)
        
        return True
    
    except Exception as e:
        logToUser("Lat, Lon values invalid: " + str(e), level = 2)
        return False 
    
def get_transformations(dataStorage):
    try:
        # get from saved project, set to local vars
        proj = dataStorage.project
        record = proj.readEntry("speckle-qgis", "transformations", "")
        if record[1] and len(record[0])>0: 
            vals: List[str] = record[0].split(";")
            dataStorage.savedTransforms.extend(vals)

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
def set_transformations(dataStorage):
    try: 
        # from widget (3 strings) to local vars AND memory (1 string)
        proj = dataStorage.project
        vals = dataStorage.savedTransforms
        transforms = ";".join(vals)
        proj.writeEntry("speckle-qgis", "transformations", transforms)
        return True
    
    except Exception as e:
        logToUser("Transformations cannot be saved: " + str(e), level = 2)
        return False 

def get_elevationLayer(dataStorage):
    try: 
        # get from saved project, set to local vars
        proj = dataStorage.project
        record = proj.readEntry("speckle-qgis", "elevationLayer", "")
        if record[1] and len(record[0])>0: 
            layerName: List[str] = record[0]
            for layer in dataStorage.all_layers:
                if layerName == layer.name():
                    dataStorage.elevationLayer = layer 
                    break 
        else: 
            dataStorage.elevationLayer = None 

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return
    
def set_elevationLayer(dataStorage):
    try: 
        # from widget (3 strings) to local vars AND memory (1 string)
        proj = dataStorage.project
        layer = getElevationLayer(dataStorage)
        name = "" 
        try: name = layer.name()
        except: pass
        proj.writeEntry("speckle-qgis", "elevationLayer", name)
        return True
    
    except Exception as e:
        logToUser("Layer cannot be saved as elevation: " + str(e), level = 2)
        return False 

def setProjectReferenceSystem(dataStorage: DataStorage, dockwidget = None):
    # Create CRS and apply to the project:
    # https://gis.stackexchange.com/questions/379199/having-problem-with-proj-string-for-custom-coordinate-system
    # https://proj.org/usage/projections.html
    try: 
        newCrsString = "+proj=tmerc +ellps=WGS84 +datum=WGS84 +units=m +no_defs +lon_0=" + str(dataStorage.custom_lon) + " lat_0=" + str(dataStorage.custom_lat) + " +x_0=0 +y_0=0 +k_0=1"
        newCrs = QgsCoordinateReferenceSystem.fromProj(newCrsString)#fromWkt(newProjWkt)
        validate = QgsCoordinateReferenceSystem().createFromProj(newCrsString)

        wkt = newCrs.toWkt()
        newCRSfromWkt = QgsCoordinateReferenceSystem.fromWkt(wkt)

        if validate: 
            srsid = trySaveCRS(newCRSfromWkt, "latlon_"+str(dataStorage.custom_lat)+"_"+str(dataStorage.custom_lon))
            crs = QgsCoordinateReferenceSystem.fromSrsId(srsid)
            dataStorage.project.setCrs(crs) 
            
            #listCrs = QgsCoordinateReferenceSystem().validSrsIds()
            #if exists == 0: newCrs.saveAsUserCrs("SpeckleCRS_lon=" + str(sPoint.x()) + "_lat=" + str(sPoint.y())) # srsid() #https://gis.stackexchange.com/questions/341500/creating-custom-crs-in-qgis
            logToUser("Custom project CRS successfully applied", level = 0, plugin=dockwidget)
        else:
            logToUser("Custom CRS could not be created", level = 1, plugin=dockwidget)
    except:
        logToUser("Custom CRS could not be created", level = 1, plugin=dockwidget)
    
    return True
