
from speckle_qgis import SpeckleQGIS
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
from ui.project_vars import set_project_streams


def populateLayerDropdown(self: SpeckleQGIS):
    if not self.dockwidget:
        return
    # Fetch the currently loaded layers
    layers = QgsProject.instance().mapLayers().values()

    # Clear the contents of the comboBox from previous runs
    self.dockwidget.layersWidget.clear()
    # Populate the comboBox with names of all the loaded layers
    #self.dockwidget.layersWidget.addItems([layer.name() for layer in layers])
    
    nameDisplay = [] 
    for layer in layers:
        if isinstance(layer, QgsRasterLayer):
            if layer.width()*layer.height() > 1000000:
                nameDisplay.append(layer.name() + " !LARGE!")
            else: nameDisplay.append(layer.name())
        
        elif isinstance(layer, QgsVectorLayer):
            if layer.featureCount() > 20000:
                nameDisplay.append(layer.name() + " !LARGE!")
            else: nameDisplay.append(layer.name())
        else: nameDisplay.append(str(layer.name()))
        
    nameDisplay.sort(key=lambda v: v.upper())
    #print(nameDisplay)
    self.dockwidget.layersWidget.addItems(nameDisplay)


def populateProjectStreams(self: SpeckleQGIS):
    if not self.dockwidget:
        return
    self.dockwidget.streamList.clear()

    self.dockwidget.streamList.addItems(
        [f"Stream not accessible - {stream[0].stream_id}" if stream[1] is None else f"{stream[1].name} - {stream[1].id}" for stream in self.current_streams]
    )
    set_project_streams(self)

def populateSurveyPoint(self: SpeckleQGIS):
    if not self.dockwidget:
        return
    try:
        self.dockwidget.surveyPointLat.clear()
        self.dockwidget.surveyPointLat.setText(str(self.lat))
        self.dockwidget.surveyPointLon.clear()
        self.dockwidget.surveyPointLon.setText(str(self.lon))
    except: return

def populateActiveStreamBranchDropdown(self: SpeckleQGIS):
    if not self.dockwidget:
        return
    self.dockwidget.streamBranchDropdown.clear()
    if self.active_stream is None or self.active_stream[1] is None or self.active_stream[1].branches is None:
        return
    self.dockwidget.streamBranchDropdown.addItems(
        [f"{branch.name}" for branch in self.active_stream[1].branches.items]
    )

def populateActiveCommitDropdown(self: SpeckleQGIS):
    if not self.dockwidget:
        return
    self.dockwidget.commitDropdown.clear()
    if self.active_stream is None:
        return
    branchName = self.dockwidget.streamBranchDropdown.currentText()
    branch = None
    if self.active_stream[1]:
        for b in self.active_stream[1].branches.items:
            if b.name == branchName:
                branch = b
                break
    try:
        self.dockwidget.commitDropdown.addItems(
            [f"{commit.id}"+ " | " + f"{commit.message}" for commit in branch.commits.items]
        )
    except: pass
