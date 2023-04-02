
import threading
import time
from typing import List
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication, QSettings, Qt, pyqtSignal, QTranslator, QRect, QObject
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget, QPushButton
from specklepy.logging import metrics
from specklepy.api.credentials import Account
from specklepy.api.models import Stream, Branch, Commit 

from specklepy.logging.exceptions import SpeckleException 
from specklepy.api.wrapper import StreamWrapper

import inspect

from ui.logger import logToUser
from ui.validation import tryGetBranch

class UpdatesLogger(QWidget):
    
    sendUpdate = pyqtSignal(str, str)

    # constructor
    def __init__(self, parent=None):
        super(UpdatesLogger, self).__init__(parent)

        self.parentWidget = parent       
        self.layout = QVBoxLayout(self)
        self.setGeometry(0, 0, 0, 0)

        dataStorage = self.parentWidget.dataStorage

        t = threading.Thread(target=self.runChecks, args=(dataStorage,))
        t.start()

    def runChecks(self, dataStorage):
        while True:
            time.sleep(5)
            #print("check")
            try:
                for url, uuid, commit_id in dataStorage.streamsToFollow:
                    #url = "https://speckle.xyz/streams/17b0b76d13/branches/random_tests"
                    url = url.split(" ")[0].split("?")[0].split("&")[0]

                    try: 
                        branch = tryGetBranch(url)
                        if isinstance(branch, Branch):
                            try:
                                latest_commit_id = branch.commits.items[0].id
                                if latest_commit_id != commit_id:
                                    self.parentWidget.updLog.sendUpdate.emit(branch.name, latest_commit_id)
                            except Exception as e:
                                logToUser(e, level = 1, func = inspect.stack()[0][3])
                                pass
                    except Exception as e:
                        logToUser(e, level = 1, func = inspect.stack()[0][3])
                        pass 
            except Exception as e:
                logToUser(e.message, level = 1, func = inspect.stack()[0][3])
                pass 
            