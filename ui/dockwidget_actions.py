
from speckle_qgis import SpeckleQGIS
from ui.add_stream_modal import AddStreamModalDialog
from ui.dockwidget_populate import populateActiveCommitDropdown, populateActiveStreamBranchDropdown, populateLayerDropdown, populateProjectStreams, populateSurveyPoint
from ui.project_vars import get_project_streams, get_survey_point, set_project_streams


def reloadUi(self: SpeckleQGIS):
    get_project_streams(self)
    populateLayerDropdown(self)
    populateProjectStreams(self)
    get_survey_point(self)
    populateSurveyPoint(self)
    self.dockwidget.streamIdField.clear()
    self.dockwidget.streamBranchDropdown.clear()
    self.dockwidget.commitDropdown.clear()
    self.dockwidget.receiveButton.setEnabled(self.is_setup)
    self.dockwidget.sendButton.setEnabled(self.is_setup)
    self.dockwidget.streams_add_button.setEnabled(self.is_setup)
    self.dockwidget.streams_remove_button.setEnabled(self.is_setup)
    self.dockwidget.streamBranchDropdown.setEnabled(self.is_setup)
    self.dockwidget.commitDropdown.setEnabled(self.is_setup)

def onStreamAddButtonClicked(self: SpeckleQGIS):
    self.add_stream_modal = AddStreamModalDialog(None)
    self.add_stream_modal.handleStreamAdd.connect(self.handleStreamAdd)
    self.add_stream_modal.show()

def onStreamRemoveButtonClicked(self: SpeckleQGIS):
    if not self.dockwidget:
        return
    index = self.dockwidget.streamList.currentIndex().row()
    #if index == 0: 
    self.current_streams.pop(index)
    self.active_stream = None
    self.dockwidget.streamBranchDropdown.clear()
    self.dockwidget.commitDropdown.clear()
    self.dockwidget.streamIdField.setText("")

    set_project_streams(self)
    populateProjectStreams(self)

def onActiveStreamChanged(self: SpeckleQGIS):
    if not self.dockwidget:
        return
    if len(self.current_streams) == 0:
        return
    index = self.dockwidget.streamList.currentRow()
    if index == -1:
        return
    try: self.active_stream = self.current_streams[index]
    except: self.active_stream = None
    self.dockwidget.streamIdField.setText(
        self.dockwidget.streamList.currentItem().text()
    )
    populateActiveStreamBranchDropdown(self)
    populateActiveCommitDropdown(self)
