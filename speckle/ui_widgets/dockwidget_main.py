import threading
from specklepy_qt_ui.qt_ui.dockwidget_main import (
    SpeckleQGISDialog as SpeckleQGISDialog_UI,
)
import specklepy_qt_ui.qt_ui

from speckle.ui_widgets.widget_transforms import MappingSendDialogQGIS

from PyQt5 import uic
import os
import inspect
from specklepy.logging.exceptions import SpeckleException
from specklepy_qt_ui.qt_ui.utils.logger import logToUser

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(
        os.path.dirname(specklepy_qt_ui.qt_ui.__file__),
        os.path.join("ui", "dockwidget_main.ui"),
    )
)


class SpeckleQGISDialog(SpeckleQGISDialog_UI, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SpeckleQGISDialog_UI, self).__init__(parent)

        self.setupUi(self)
        self.runAllSetup()

    def createMappingDialog(self, plugin):
        if self.mappingSendDialog is None:
            self.mappingSendDialog = MappingSendDialogQGIS(None)
            self.mappingSendDialog.dataStorage = self.dataStorage
            self.mappingSendDialog.dialog_button.disconnect()
            self.mappingSendDialog.dialog_button.clicked.connect(
                lambda: self.read_elevation_from_dialog(plugin)
            )

        self.mappingSendDialog.runSetup()

    def read_elevation_from_dialog(self, plugin):
        self.dataStorage = self.mappingSendDialog.saveElevationLayer()
        plugin.dataStorage = self.dataStorage
        self.mappingSendDialog.close()

    def completeStreamSection(self, plugin):
        try:
            self.streams_remove_button.clicked.connect(
                lambda: self.onStreamRemoveButtonClicked(plugin)
            )
            self.streamList.currentIndexChanged.connect(
                lambda: self.onActiveStreamChanged(plugin)
            )
            self.streamBranchDropdown.currentIndexChanged.connect(
                lambda: self.populateActiveCommitDropdown(plugin)
            )
            return
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self)
            return

    def onStreamRemoveButtonClicked(self, plugin):
        try:
            from speckle.utils.project_vars import set_project_streams

            if not self:
                return
            index = self.streamList.currentIndex()
            if len(plugin.current_streams) > 0:
                plugin.current_streams.pop(index)
            plugin.active_stream = None
            self.streamBranchDropdown.clear()
            self.commitDropdown.clear()

            set_project_streams(plugin)
            self.populateProjectStreams(plugin)
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self)
            return

    def populateProjectStreams(self, plugin):
        try:
            from speckle.utils.project_vars import set_project_streams

            if not self:
                return
            self.streamList.clear()
            for stream in plugin.current_streams:
                self.streamList.addItems(
                    [
                        (
                            f"Stream not accessible - {stream[0].stream_id}"
                            if stream[1] is None
                            or isinstance(stream[1], SpeckleException)
                            else f"{stream[1].name}, {stream[1].id} | {stream[0].stream_url.split('/streams')[0].split('/projects')[0]}"
                        )
                    ]
                )
            if len(plugin.current_streams) == 0:
                self.streamList.addItems([""])
            self.streamList.addItems(["Create New Stream"])
            set_project_streams(plugin)
            index = self.streamList.currentIndex()
            if index == -1:
                self.streams_remove_button.setEnabled(False)
            else:
                self.streams_remove_button.setEnabled(True)

            if len(plugin.current_streams) > 0:
                plugin.active_stream = plugin.current_streams[0]
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self)
            return

    def cancelOperations(self):
        for t in threading.enumerate():
            if "speckle_" in t.name:
                t.kill()
                t.join()

    def overwriteStartSettings(self):
        self.reportBtn.disconnect()
        self.reportBtn.clicked.connect(self.showDebugReport)

    def showDebugReport(self):
        from plugin_utils.installer import _debug

        self.msgLog.showReport()
        if _debug is True:
            text = ""
            report_new = self.dataStorage.flat_report_receive
            report_old = self.dataStorage.flat_report_latest

            for key, val in report_new.items():
                if key in report_old:
                    if report_new[key]["hash"] != report_old[key]["hash"]:
                        diff: str = "GEOMETRY"
                        if (
                            report_old[key]["attributes"]
                            != report_new[key]["attributes"]
                        ):
                            diff = "ATTRIBUTES"
                            if (
                                report_old[key]["geometry"]
                                != report_new[key]["geometry"]
                            ):
                                diff = "BOTH"

                        # add symbol
                        if diff == "ATTRIBUTES":
                            text += "🔶 "
                        elif diff == "GEOMETRY":
                            text += "🔷 "
                        else:
                            text += "🔷🔶 "

                        # basic report item
                        report_item = {
                            key: {
                                "diff": diff,
                                "layer_name": report_new[key]["layer_name"],
                                "speckle_ids": [
                                    report_old[key]["speckle_id"],
                                    report_new[key]["speckle_id"],
                                ],
                            }
                        }
                        text += str(report_item) + "\n"

                        # add details about diff
                        if diff in ["ATTRIBUTES", "GEOMETRY"]:
                            extra_report_item = {
                                diff.lower(): [
                                    report_old[key][diff.lower()],
                                ]
                            }
                            text += str(extra_report_item) + "\n"
                            extra_report_item = {
                                diff.lower(): [
                                    report_new[key][diff.lower()],
                                ]
                            }
                            text += str(extra_report_item) + "\n" + "\n"
                        else:
                            for keyword in ["ATTRIBUTES", "GEOMETRY"]:
                                extra_report_item = {
                                    keyword.lower(): [
                                        report_old[key][keyword.lower()],
                                    ]
                                }
                                text += str(extra_report_item) + "\n"
                                extra_report_item = {
                                    keyword.lower(): [
                                        report_new[key][keyword.lower()],
                                    ]
                                }
                                text += str(extra_report_item) + "\n" + "\n"

                else:
                    report_item = {
                        key: {
                            "diff": "ADDED",
                            "layer_name": report_new[key]["layer_name"],
                            "speckle_ids": [
                                report_new[key]["speckle_id"],
                            ],
                        }
                    }
                    text += "✅ "
                    text += str(report_item) + "\n" + "\n"

            for key, val in report_old.items():
                if key not in report_new:
                    report_item = {
                        key: {
                            "diff": "DELETED",
                            "layer_name": report_old[key]["layer_name"],
                            "speckle_ids": [
                                report_old[key]["speckle_id"],
                            ],
                        }
                    }
                    text += "❌ "
                    text += str(report_item) + "\n" + "\n"

            self.msgLog.reportDialog.report_text.setText(str(text))
