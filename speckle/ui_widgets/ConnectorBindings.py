
from typing import Dict, List

from numpy import double
from import UpdateSavedStreams
from import UpdateSelectedStream

from specklepy_qt_ui.qt_ui.ConnectorBindings import ConnectorBindings
from specklepy_qt_ui.qt_ui.Models.StreamState import StreamState

class QGISBindings(ConnectorBindings):

    def __init__(self):
        pass 
    
    def UpdateSavedStreams(self, streams: List[StreamState]):
        UpdateSavedStreams(streams)

    def UpdateSelectedStream(self): 
        UpdateSelectedStream()

    def Open3DView(self, viewCoordinates: List[double],  viewName: str = ""):
        '''Opens a 3D view in the host application
        viewCoordinates: First three values are the camera position, second three the target.
        viewName: Id or Name of the view'''
        return 

    def GetHostAppNameVersion(self)-> str:
        '''Gets the current host application name with version.'''
        return

    def GetHostAppName(self) -> str:
        '''Gets the current host application name.'''
        return

    def GetFileName(self) -> str:
        '''Gets the current opened/focused file's name.
        Make sure to check regarding unsaved/temporary files.'''
        return

    def GetDocumentId(self) -> str:
        '''Gets the current opened/focused file's id.
        Generate one in here if the host app does not provide one.'''
        return 

    def GetDocumentLocation(self) -> str:
        '''Gets the current opened/focused file's locations.
        Make sure to check regarding unsaved/temporary files.'''
        return

    def ResetDocument(self):
        '''Clears the document state of selections and previews'''
        return

    def GetActiveViewName(self) -> str:
        '''Gets the current opened/focused file's view, if applicable.'''
        return

    def GetStreamsInFile(self) -> List[StreamState]:
        '''Returns the serialised clients present in the current open host file.'''
        return 

    def WriteStreamsToFile(self, streams: List[StreamState]):
        '''Writes serialised clients to the current open host file.'''
        return

    def AddNewStream(self, state: StreamState):
        '''Adds a new client and persists the info to the host file'''
        return

    def PersistAndUpdateStreamInFile(self, state: StreamState):
        '''Persists the stream info to the host file; if maintaining a local in memory copy, make sure to update it too.'''
        return 
    
    def  SendStream(self, state: StreamState, progress: ProgressViewModel) -> str:
        '''Pushes a client's stream'''
        return

    def PreviewSend(self, state: StreamState, progress: ProgressViewModel):
        '''Previews a send operation'''

    def ReceiveStream(self, state: StreamState, progress: ProgressViewModel) -> StreamState:
        '''Receives stream data from the server'''

    def PreviewReceive(self, state: StreamState, progress: ProgressViewModel) -> StreamState:
        '''Previews a receive operation'''

    def GetSelectedObjects(self) -> List[str]: 
        '''Adds the current selection to the provided client.'''

    def GetObjectsInView(self) -> List[str]:
        '''Gets a list of objects in the currently active view'''

    def SelectClientObjects(self, objs: List[str], deselect: bool = False):
        '''clients should be able to select/preview/hover one way or another their associated objects'''

    def GetSelectionFilters(self) -> List[ISelectionFilter]:
        '''Should return a list of filters that the application supports.'''

    def GetReceiveModes(self) -> List[ReceiveMode]:
        '''Should return a list of receive modes that the application supports.'''

    def GetCustomStreamMenuItems(self) -> List[MenuItem]:
        '''Return a list of custom menu items for stream cards.'''

    def GetSettings(self) -> List[ISetting]:
        return

    def ImportFamilyCommand(self, Mapping: Dict[str, List[MappingValue]]  ) -> Dict[str, List[MappingValue]] :
        '''Imports family symbols in Revit'''
        return 
