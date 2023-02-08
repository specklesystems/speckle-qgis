import os
from typing import List, Tuple, Union
import ui.speckle_qgis_dialog
from qgis.core import Qgis

from speckle.logging import logger
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtCore import pyqtSignal
from specklepy.api.models import Stream
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException
from speckle.utils import logger
from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "create_branch.ui")
)

class CreateBranchModalDialog(QtWidgets.QWidget, FORM_CLASS):

    name_field: QtWidgets.QLineEdit = None
    description_field: QtWidgets.QLineEdit = None
    dialog_button_box: QtWidgets.QDialogButtonBox = None
    speckle_client: Union[SpeckleClient, None] = None

    #Events
    handleBranchCreate = pyqtSignal(str,str)

    def __init__(self, parent=None, speckle_client: SpeckleClient = None):
        super(CreateBranchModalDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        self.speckle_client = speckle_client
        self.setupUi(self)
        self.setWindowTitle("Create New Branch")

        self.name_field.textChanged.connect(self.nameCheck)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)

    def nameCheck(self):
        if len(self.name_field.text()) >= 3:
            self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        else: 
            self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
        return

    def onOkClicked(self):
        try:
            name = self.name_field.text()
            description = self.description_field.text()
            self.handleBranchCreate.emit(name, description)
            self.close()
        except Exception as e:
            logger.logToUser(str(e), Qgis.Warning)
            return 

    def onCancelClicked(self):
        self.close()

    def onAccountSelected(self, index):
        account = self.speckle_accounts[index]
        self.speckle_client = SpeckleClient(account.serverInfo.url, account.serverInfo.url.startswith("https"))
        self.speckle_client.authenticate_with_token(token=account.token)
