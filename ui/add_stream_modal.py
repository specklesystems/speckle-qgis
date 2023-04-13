import inspect
import os
from typing import List, Union
from ui.logger import logToUser
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
#from specklepy.logging import metrics
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

        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 

        self.search_button.clicked.connect(self.onSearchClicked)
        self.search_results_list.currentItemChanged.connect( self.searchResultChanged )
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        self.accounts_dropdown.currentIndexChanged.connect(self.onAccountSelected)
        self.populate_accounts_dropdown()

    def searchResultChanged(self):
        try:
            index = self.search_results_list.currentIndex().row()
            if index == -1: self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
            else: self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def onSearchClicked(self):
        try:
            query = self.search_text_field.text()
            sw = None 
            results = []
            if "http" in query and len(query.split("/")) >= 3: # URL
                sw = StreamWrapper(query)
                stream = sw.get_client().stream.get(sw.stream_id)
                if isinstance(stream, Stream): results = [stream]
                else: results = []
            
            elif self.speckle_client is not None: 
                results = self.speckle_client.stream.search(query)
            elif self.speckle_client is None: 
                logToUser(f"Account cannot be authenticated: {self.accounts_dropdown.currentText()}", level = 1, func = inspect.stack()[0][3]) 
            
            self.stream_results = results
            self.populateResultsList(sw)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return
    
    def populateResultsList(self, sw):
        try:
            self.search_results_list.clear()
            if isinstance(self.stream_results, SpeckleException): 
                logToUser("Some streams cannot be accessed", level = 1, func = inspect.stack()[0][3])
                return 
            for stream in self.stream_results:
                host = ""
                if sw is not None:
                    host = sw.get_account().serverInfo.url
                else: 
                    host = self.speckle_client.account.serverInfo.url
                
                if isinstance(stream, SpeckleException): 
                    logToUser("Some streams cannot be accessed", level = 1, func = inspect.stack()[0][3])
                else: 
                    self.search_results_list.addItems([
                        f"{stream.name}, {stream.id} | {host}" #for stream in self.stream_results 
                    ])
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def onOkClicked(self):
        try:
            if isinstance(self.stream_results, SpeckleException):
                logToUser("Selected stream cannot be accessed: "+ str(self.stream_results.message), level = 1, func = inspect.stack()[0][3])
                return
            #elif index == -1 or len(self.stream_results) == 0:
            #    logger.logToUser("Select stream from \"Search Results\". No stream selected", Qgis.Warning)
            #    return 
            else:
                try:
                    index = self.search_results_list.currentIndex().row()
                    stream = self.stream_results[index]
                    item = self.search_results_list.item(index)
                    url = item.text().split(" | ")[1] + "/streams/" + item.text().split(", ")[1].split(" | ")[0]
                    sw = StreamWrapper(url) 
                    #acc = sw.get_account() #get_local_accounts()[self.accounts_dropdown.currentIndex()]
                    self.handleStreamAdd.emit(sw) #StreamWrapper(f"{acc.serverInfo.url}/streams/{stream.id}?u={acc.userInfo.id}"))
                    self.close()
                except Exception as e:
                    logToUser("Some streams cannot be accessed: " + str(e), level = 1, func = inspect.stack()[0][3])
                    return 
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def onCancelClicked(self):
        try:
            self.close()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def onAccountSelected(self, index):
        try:
            account = self.speckle_accounts[index]
            self.speckle_client = SpeckleClient(account.serverInfo.url, account.serverInfo.url.startswith("https"))
            self.speckle_client.authenticate_with_token(token=account.token)
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def populate_accounts_dropdown(self):
        try:
            # Populate the accounts comboBox
            self.speckle_accounts = get_local_accounts()
            self.accounts_dropdown.clear()
            self.accounts_dropdown.addItems(
                [
                    f"{acc.userInfo.name}, {acc.userInfo.email} | {acc.serverInfo.url}"
                    for acc in self.speckle_accounts
                ]
            )
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

