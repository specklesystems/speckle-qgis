import os
from typing import List, Union
import ui.speckle_qgis_dialog
from qgis.core import Qgis

from speckle.logging import logger
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtCore import pyqtSignal
from specklepy.api.models import Stream
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException
from speckle.utils import logger
from specklepy.api.credentials import get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "add_stream_modal.ui")
)

class AddStreamModalDialog(QtWidgets.QWidget, FORM_CLASS):

    search_button: QtWidgets.QPushButton = None
    search_text_field: QtWidgets.QLineEdit = None
    search_results_list: QtWidgets.QListWidget = None
    dialog_button_box: QtWidgets.QDialogButtonBox = None
    accounts_dropdown: QtWidgets.QComboBox

    stream_results: List[Stream] = []
    speckle_client: Union[SpeckleClient, None] = None

    #Events
    handleStreamAdd = pyqtSignal(StreamWrapper)

    def __init__(self, parent=None, speckle_client: SpeckleClient = None):
        super(AddStreamModalDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        self.speckle_client = speckle_client
        self.setupUi(self)
        self.setWindowTitle("Add Speckle stream")

        self.search_button.clicked.connect(self.onSearchClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        self.accounts_dropdown.currentIndexChanged.connect(self.onAccountSelected)
        self.populate_accounts_dropdown()

    def onSearchClicked(self):
        query = self.search_text_field.text()
        if "http" in query and len(query.split("/")) >= 3: # URL
            steamId = query
            try: steamId = query.split("/streams/")[1].split("/")[0] 
            except: pass

            stream = self.speckle_client.stream.get(steamId)
            if isinstance(stream, Stream): results = [stream]
            else: results = []
           
        else: 
            results = self.speckle_client.stream.search(query)
        
        self.stream_results = results
        #print(results)
        self.populateResultsList()
    
    def populateResultsList(self):
        self.search_results_list.clear()
        if isinstance(self.stream_results, SpeckleException): 
            logger.logToUser("Some streams cannot be accessed", Qgis.Warning)
            return 
        for stream in self.stream_results:
            if isinstance(stream, SpeckleException): 
                logger.logToUser("Some streams cannot be accessed", Qgis.Warning)
            else: 
                self.search_results_list.addItems([
                    f"{stream.name} - {stream.id}" #for stream in self.stream_results 
                ])

    def onOkClicked(self):
        if isinstance(self.stream_results, SpeckleException):
            logger.logToUser("Selected stream cannot be accessed", Qgis.Warning)
            return
        elif index == -1 or len(self.stream_results) == 0:
            logger.logToUser("Select stream from \"Search Results\". No stream selected", Qgis.Warning)
            return 
        else:
            try:
                index = self.search_results_list.currentIndex().row()
                stream = self.stream_results[index]
                acc = get_local_accounts()[self.accounts_dropdown.currentIndex()]
                self.handleStreamAdd.emit(StreamWrapper(f"{acc.serverInfo.url}/streams/{stream.id}?u={acc.userInfo.id}"))
                self.close()
            except Exception as e:
                logger.logToUser("Some streams cannot be accessed: " + str(e), Qgis.Warning)
                return 

    def onCancelClicked(self):
        self.close()

    def onAccountSelected(self, index):
        account = self.speckle_accounts[index]
        self.speckle_client = SpeckleClient(account.serverInfo.url, account.serverInfo.url.startswith("https"))
        self.speckle_client.authenticate_with_token(token=account.token)

    def populate_accounts_dropdown(self):
        # Populate the accounts comboBox
        self.speckle_accounts = get_local_accounts()
        self.accounts_dropdown.clear()
        self.accounts_dropdown.addItems(
            [
                f"{acc.userInfo.name} - {acc.serverInfo.url}"
                for acc in self.speckle_accounts
            ]
        )

