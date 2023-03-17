import inspect
import os
from typing import List, Tuple, Union
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
from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "create_stream.ui")
)

class CreateStreamModalDialog(QtWidgets.QWidget, FORM_CLASS):

    name_field: QtWidgets.QLineEdit = None
    description_field: QtWidgets.QLineEdit = None
    dialog_button_box: QtWidgets.QDialogButtonBox = None
    accounts_dropdown: QtWidgets.QComboBox
    public_toggle: QtWidgets.QCheckBox

    speckle_client: Union[SpeckleClient, None] = None

    #Events
    handleStreamCreate = pyqtSignal(Account, str, str, bool)

    def __init__(self, parent=None, speckle_client: SpeckleClient = None):
        super(CreateStreamModalDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        self.speckle_client = speckle_client
        self.setupUi(self)
        self.setWindowTitle("Create New Stream")

        self.name_field.textChanged.connect(self.nameCheck)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        self.accounts_dropdown.currentIndexChanged.connect(self.onAccountSelected)
        self.populate_accounts_dropdown()

    def nameCheck(self):
        try:
            if len(self.name_field.text()) == 0 or len(self.name_field.text()) >= 3:
                self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
            else: 
                self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
            return
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def onOkClicked(self):
        try:
            acc = get_local_accounts()[self.accounts_dropdown.currentIndex()]
            name = self.name_field.text()
            description = self.description_field.text()
            public = self.public_toggle.isChecked()
            self.handleStreamCreate.emit(acc,name,description,public)
            self.close()
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3])
            return

    def onCancelClicked(self):
        try:
            #self.handleCancelStreamCreate.emit()
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

