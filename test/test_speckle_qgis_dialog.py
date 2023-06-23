# coding=utf-8
"""Dialog test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = "alan@speckle.systems"
__date__ = "2021-08-04"
__copyright__ = "Copyright 2021, Speckle Systems"

import unittest

from qgis.PyQt.QtWidgets import QDialogButtonBox, QDialog

from specklepy_qt_ui.qt_ui.dockwidget_main import SpeckleQGISDialog

from utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class SpeckleQGISDialogTest(unittest.TestCase):
    """Test dialog works."""

    def setUp(self):
        """Runs before each test."""
        self.dialog = SpeckleQGISDialog(None)

    def tearDown(self):
        """Runs after each test."""
        self.dialog = None

    def test_dialog_ok(self):
        """Test we can click OK."""

        button = self.dialog.button_box.button(QDialogButtonBox.Ok)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Accepted)

    def test_dialog_cancel(self):
        """Test we can click cancel."""
        button = self.dialog.button_box.button(QDialogButtonBox.Cancel)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.Rejected)


if __name__ == "__main__":
    suite = unittest.makeSuite(SpeckleQGISDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
