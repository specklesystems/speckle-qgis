
from qgis.core import Qgis, QgsProject,QgsVectorLayer, QgsRasterLayer, QgsIconUtils 
from specklepy.logging.exceptions import (SpeckleException, GraphQLException)
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt import QtGui
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import QCheckBox, QListWidgetItem, QAction, QDockWidget, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import pyqtSignal, Qt 

#from qgis.PyQt import QtCore, QtWidgets #, QtWebEngineWidgets
from PyQt5 import *


try:
    #from plotly.graph_objects import Figure, Scatter
    #import plotly
    #import pyqtgraph
    #from pyqtgraph import PlotWidget, plot
    #import pyqtgraph as pg
    import plotly.express as px
    from PyQt5.QtWebKitWidgets import QWebView
    #from PyQtWebEngine import * 
except: 
    import os; import sys; import subprocess; pythonExec = os.path.dirname(sys.executable) + "\\python3"
    #result = subprocess.run([pythonExec, "-m", "pip", "install", "pyqtgraph"], capture_output=True, text=True, shell=True, timeout=1000); print(result)
    result = subprocess.run([pythonExec, "-m", "pip", "install", "plotly"], capture_output=True, text=True, shell=True, timeout=1000); print(result)
    result = subprocess.run([pythonExec, "-m", "pip", "install", "PyQtWebEngine"], capture_output=True, text=True, shell=True, timeout=1000); print(result)

    #from pyqtgraph import PlotWidget, plot
    #import pyqtgraph as pg
    import plotly.express as px

import os 

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "speckle_qgis_dashboard.ui")
)


class SpeckleDashboard(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    dataNumeric: dict
    dataText: dict 
    dataWidget: QtWidgets.QListWidget
    chart: QWidget
    browser = None
    
    def __init__(self, parent=None):
        """Constructor."""
        super(SpeckleDashboard, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        
        self.browser = QWebView(self) # https://github.com/qgis/QGIS/issues/26048
        self.setupUi(self)
    
    def setup(self):
        for i, (key, val) in enumerate(self.dataNumeric.items()): 
            listItem = QListWidgetItem( f"{key}: {val}" ) 
            self.dataWidget.addItem(listItem)
        

    def update(self, layer):

        self.dataNumeric = {}
        self.dataText = {}

        fields = layer.fields()
        for i, key in enumerate(fields.names()): 
            if key in ["Branch URL","commit_id"]: continue

            value = None
            variant = fields.at(i).type()

            if variant == 10: value = []
            if variant == 6: value = 0

            for feat in layer.getFeatures():
                if variant == 10:
                    value.extend(feat[key].replace("[","").replace("]","").split(","))
                elif variant == 6:
                    value += feat[key]
            
            if variant == 10: self.dataText.update({key: value})
            if variant == 6: self.dataNumeric.update({key: value})

        self.setup()
        self.createChart()
        
    def createChart(self):

        # https://stackoverflow.com/questions/60522103/how-to-have-plotly-graph-as-pyqt5-widget 
        df = px.data.tips()
        fig = px.box(df, x="day", y="total_bill", color="smoker")
        fig.update_traces(quartilemethod="exclusive") # or "inclusive", or "linear" by default
        self.browser.setHtml(fig.to_html(include_plotlyjs='cdn'))

        # remove all buttons
        try:
            for i in reversed(range(self.chart.layout.count())): 
                self.chart.layout.itemAt(i).widget().setParent(None)
        except: pass 

        self.chart.layout = QHBoxLayout(self.chart)
        self.browser.setMaximumHeight(400)
        self.chart.layout.addWidget(self.browser)

        return 
        # https://www.pythonguis.com/tutorials/plotting-pyqtgraph/

        graphWidget = pg.PlotWidget()

        hour = [1,2,3,4,5,6,7,8,9,10]
        temperature = [30,32,34,32,33,31,29,32,35,45]

        # plot data: x, y values
        graphWidget.plot(hour, temperature)
        
        # remove all buttons
        try:
            for i in reversed(range(self.chart.layout.count())): 
                self.chart.layout.itemAt(i).widget().setParent(None)
        except: pass 

        self.chart.layout = QHBoxLayout(self.chart)
        self.chart.layout.addWidget(graphWidget)

        # set the QWebEngineView instance as main widget
        #self.setCentralWidget(plot_widget)        

