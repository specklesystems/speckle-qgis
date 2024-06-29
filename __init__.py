# -*- coding: utf-8 -*-

import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

try:
    from plugin_utils.installer import ensure_dependencies, startDebugger
    from speckle.utils.panel_logging import logger

    from qgis.core import Qgis

    # noinspection PyPep8Naming
    def classFactory(iface):  # pylint: disable=invalid-name
        """Load SpeckleQGIS class from file SpeckleQGIS.

        :param iface: A QGIS interface instance.
        :type iface: QgsInterface
        """

        # Set qgisInterface to enable logToUser notifications
        logger.qgisInterface = iface
        iface.pluginToolBar().setVisible(True)

        # Ensure dependencies are installed in the machine
        startDebugger()
        ensure_dependencies("QGIS")

        from speckle_qgis import SpeckleQGIS
        from specklepy.logging import metrics

        version = (
            Qgis.QGIS_VERSION.encode("iso-8859-1", errors="ignore")
            .decode("utf-8")
            .split(".")[0]
        )
        metrics.set_host_app("QGIS", f"QGIS{version}")
        return SpeckleQGIS(iface)

    class EmptyClass:
        # https://docs.qgis.org/3.28/en/docs/pyqgis_developer_cookbook/plugins/plugins.html#mainplugin-py
        def __init__(self, iface):
            pass

        def initGui(self):
            pass

        def unload(self):
            pass

except ModuleNotFoundError:
    pass
