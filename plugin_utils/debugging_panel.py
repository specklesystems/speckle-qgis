from typing import Optional
from specklepy.objects import Base
from specklepy.objects.geometry import Point, Line, Mesh
from specklepy.objects.other import RevitParameter

# run testing locally:
# in .toml:
# [tool.pytest.ini_options]
# pythonpath = "speckle"
# pytest -o console_output_style=classic
# poetry self add poetry-dotenv-plugin
# https://pypi.org/project/poetry-dotenv-plugin/
# USE_PATH_FOR_GDAL_PYTHON=YES

# from OSGeo4W shell: 
# "C:\Program Files\QGIS 3.34.1\bin\python-qgis.bat" -m pip install pytest
# python -m pytest -cov C:\Users\katri\AppData\Roaming\QGIS\QGIS3\profiles\development\python\plugins\speckle-qgis\ 

# "C:\Program Files\QGIS 3.34.1\bin\python-qgis.bat" C:\Users\katri\AppData\Roaming\QGIS\QGIS3\profiles\development\python\plugins\speckle-qgis\tests_qgis\unit\geometry_tests\test_point_mixed.py 

def someF(path):
    import importlib.util
    import sys

    if "/" in path:
        name = path.split("/")[-2]
    else:
        name = path.split("\\")[-2]
    spec = importlib.util.spec_from_file_location(name, path)
    foo = importlib.util.module_from_spec(spec)
    sys.modules[name] = foo
    spec.loader.exec_module(foo)
    return foo
    # foo.MyClass()


import types


def reload_package(root_module):
    package_name = root_module.__name__
    # get a reference to each loaded module
    loaded_package_modules = dict(
        [
            (key, value)
            for key, value in sys.modules.items()
            if key.startswith(package_name) and isinstance(value, types.ModuleType)
        ]
    )
    # delete references to these loaded modules from sys.modules
    for key in loaded_package_modules:
        del sys.modules[key]
    # load each of the modules again;
    # make old modules share state with new modules
    for key in loaded_package_modules:
        print("loading %s" % key)
        newmodule = __import__(key)
        oldmodule = loaded_package_modules[key]
        oldmodule.__dict__.clear()
        oldmodule.__dict__.update(newmodule.__dict__)


path = r"C:\Users\katri\AppData\Roaming\Speckle\connector_installations\QGIS\urllib3\__init__.py"
someF(path)
import os
import inspect
import external_def

from importlib import reload
import urllib3

urllib3 = reload(urllib3)

####################
import os, sys
from subprocess import run

path = r"C:\Users\katri\AppData\Roaming\Speckle\connector_installations\QGIS"
pythonExec = os.path.dirname(sys.executable) + "\\python3.exe"
pythonExec = r"C:\Program Files\QGIS 3.32.2\apps\Python39\python3.exe"
completed_process = run(
    [pythonExec, "-m", "pip", "install", "-t", path, "requests-toolbelt==1.0.0"],
    capture_output=True,
    text=True,
)


#################################
class RevitDirectShape(Base, speckle_type="Objects.BuiltElements.Revit.DirectShape"):
    name: str = ""
    type: str = ""
    category: int = 49
    elementId: Optional[str]
    parameters = Base()
    isRevitLinkedModel: bool = False
    revitLinkedModelPath: str = ""
    baseGeometries: Optional[list]
    phaseCreated: str = "New Construction"


def createCommit():
    from specklepy.objects.other import Collection

    base_obj = Collection(
        units="m", collectionType="Python commit", name="Python commit", elements=[]
    )

    element = RevitDirectShape()
    mesh = Mesh().create(vertices=[0, 0, 0, 100, 0, 0, 0, 100, 0], faces=[3, 0, 1, 2])
    element.baseGeometries = [mesh]

    # text param
    name_1 = "text_param"
    element.parameters[name_1] = RevitParameter()
    element.parameters[name_1].isTypeParameter = False
    element.parameters[name_1].value = "some text here"
    element.parameters[
        name_1
    ].applicationUnitType = (
        "autodesk.spec:spec.string-2.0.0"  # "autodesk.spec:spec.string-2.0.0"
    )
    element.parameters[name_1].applicationInternalName = "text_param"

    # numeric param
    name_2 = "number_param"
    element.parameters[name_2] = RevitParameter()
    element.parameters[name_2].isTypeParameter = False
    element.parameters[name_2].value = 1122
    element.parameters[name_2].applicationUnit = "autodesk.unit.unit:centimeters-1.0.1"
    element.parameters[
        name_2
    ].applicationUnitType = (
        "autodesk.spec.aec:distance-2.0.0"  # "autodesk.spec:spec.string-2.0.0"
    )
    element.parameters[name_2].applicationInternalName = name_2

    base_obj.elements.append(element)
    return base_obj


def sendCommit(stream_id=""):
    import specklepy

    print(specklepy.__file__)
    from specklepy.core.api.client import SpeckleClient
    from specklepy.transports.server import ServerTransport
    from specklepy.core.api import operations
    from specklepy.core.api.credentials import get_local_accounts

    account = get_local_accounts()[2]
    client = SpeckleClient(
        account.serverInfo.url, account.serverInfo.url.startswith("https")
    )

    client.authenticate_with_account(account)
    if client.account.token is not None:
        stream = client.stream.get(id=stream_id, branch_limit=100, commit_limit=100)
    else:
        print("fail")
    transport = ServerTransport(client=client, stream_id=stream_id)

    base_obj = createCommit()
    print(base_obj)
    print(account)
    print(client)
    print(stream_id)
    print(transport)

    objId = operations.send(base=base_obj, transports=[transport])
    commit_id = client.commit.create(
        stream_id=stream_id,
        object_id=objId,
        branch_name="main",
        message="Sent objects from Python",
        source_application="Python",
    )
    print(commit_id)
    return


sendCommit(stream_id="17b0b76d13")

exit()


def checkGQLerror():
    import gql, requests, urllib3, specklepy
    from importlib.metadata import version

    version("gql")
    version("requests")
    version("urllib3")
    version("specklepy")
    from specklepy.core.api.client import SpeckleClient
    from specklepy.core.api.credentials import get_local_accounts

    account = get_local_accounts()[0]
    print(account)
    new_client = SpeckleClient(
        account.serverInfo.url, account.serverInfo.url.startswith("https")
    )
    print(new_client)
    new_client.authenticate_with_token(token=account.token)
    print(new_client)


r"""
layer = QgsVectorLayer('CompoundCurve?crs=epsg:4326', 'polygon' , 'memory')
prov = layer.dataProvider()
feat = QgsFeature()
c = QgsCompoundCurve()
c.addCurve(QgsCircularString(QgsPoint(-2,0,0),QgsPoint(-2,-2,0),QgsPoint(-4,-1,0)))
feat.setGeometry(c)
prov.addFeatures([feat])
QgsProject.instance().addMapLayer(layer, True)
"""
#### get layers
project = QgsProject.instance()
projectCRS = project.crs()
layerTreeRoot = project.layerTreeRoot()


def getLayers(tree: QgsLayerTree, parent: QgsLayerTreeNode):
    children = parent.children()
    layers = []
    for node in children:
        if tree.isLayer(node):
            if isinstance(node.layer(), QgsVectorLayer) or isinstance(
                node.layer(), QgsRasterLayer
            ):
                layers.append(node)
            continue
        if tree.isGroup(node):
            for lyr in getLayers(tree, node):
                if isinstance(lyr.layer(), QgsVectorLayer) or isinstance(
                    lyr.layer(), QgsRasterLayer
                ):
                    layers.append(lyr)
            # layers.extend( [ lyr for lyr in getLayers(tree, node) if isinstance(lyr.layer(), QgsVectorLayer) or isinstance(lyr.layer(), QgsRasterLayer) ] )
    return layers


layers = getLayers(layerTreeRoot, layerTreeRoot)
print(layers)
layer = layers[0].layer()

# layers[0].layer().loadNamedStyle(r'renderer3d.qml')

######################################## rasters ################################
raster_layer = layers[5].layer()

dataProvider = raster_layer.dataProvider()

########### singleband
band = 1
contrast = QgsContrastEnhancement()
contrast.setContrastEnhancementAlgorithm(1)
contrast.setMaximumValue(100)
contrast.setMinimumValue(0)

rendererNew = QgsSingleBandGrayRenderer(dataProvider, int(band))
rendererNew.setContrastEnhancement(contrast)

############ multiband
redBand = 1
greenBand = 2
blueBand = 3
rendererNew = QgsMultiBandColorRenderer(
    dataProvider, int(redBand), int(greenBand), int(blueBand)
)

contrastR = QgsContrastEnhancement()
contrastR.setContrastEnhancementAlgorithm(1)
contrastR.setMaximumValue(10000)
contrastR.setMinimumValue(0)
# rendererNew.setRedContrastEnhancement(contrastR)

rendererNew.minMaxOrigin().setLimits(QgsRasterMinMaxOrigin.Limits(1))

raster_layer.setRenderer(rendererNew)


###################################################### triangulation


def fix_orientation(polyBorder, positive=True, coef=1):
    # polyBorder = [QgsPoint(-1.42681236722918436,0.25275926575812246), QgsPoint(-1.42314917758289616,0.78756097253123281), QgsPoint(-0.83703883417681257,0.77290957257654203), QgsPoint(-0.85169159276196471,0.24176979917208921), QgsPoint(-1.42681236722918436,0.25275926575812246)]
    sum_orientation = 0
    for k, ptt in enumerate(polyBorder):  # pointList:
        index = k + 1
        if k == len(polyBorder) - 1:
            index = 0
        pt = polyBorder[k * coef]
        pt2 = polyBorder[index * coef]
        # print(pt)
        try:
            sum_orientation += (pt2.x - pt.x) * (pt2.y + pt.y)  # if Speckle Points
        except:
            sum_orientation += (pt2.x() - pt.x()) * (pt2.y() + pt.y())  # if QGIS Points
    if positive is True:
        if sum_orientation < 0:
            polyBorder.reverse()
    else:
        if sum_orientation > 0:
            polyBorder.reverse()
    return polyBorder


def getHolePt(pointListLocal):
    pointListLocal = fix_orientation(pointListLocal, True, 1)
    minXpt = pointListLocal[0]
    index = 0
    index2 = 1
    for i, pt in enumerate(pointListLocal):
        if pt.x() < minXpt.x():
            minXpt = pt
            index = i
            if i == len(pointListLocal) - 1:
                index2 = 0
            else:
                index2 = index + 1
    x_range = pointListLocal[index2].x() - minXpt.x()
    y_range = pointListLocal[index2].y() - minXpt.y()
    if y_range > 0:
        sidePt = [minXpt.x() + x_range / 2 + 0.00000000001, minXpt.y() + y_range / 2]
    else:
        sidePt = [minXpt.x() + x_range / 2 - 0.00000000001, minXpt.y() + y_range / 2]
    return sidePt


def getPolyBoundary(geom):
    vertices = []
    segmList = []
    holes = []
    try:
        extRing = geom.exteriorRing()
        pt_iterator = extRing.vertices()
    except:
        try:
            extRing = geom.constGet().exteriorRing()
            pt_iterator = geom.vertices()
        except:
            extRing = geom
            pt_iterator = geom.vertices()
    pointListLocal = []
    startLen = len(vertices)
    for pt in enumerate(pt_iterator):
        pointListLocal.append(pt)
    for i, pt in enumerate(pointListLocal):
        # print(pt)
        vertices.append([pt[1].x(), pt[1].y()])
        if i > 0:
            segmList.append([startLen + i - 1, startLen + i])
        if i == len(pointListLocal) - 1:  # also add a cap
            segmList.append([startLen + i, startLen])
    ########### get voids
    try:
        for i in range(geom.numInteriorRings()):
            intRing = geom.interiorRing(i)
            pt_iterator = geom.vertices()
            pointListLocal = []
            startLen = len(vertices)
            for pt in pt_iterator:
                pointListLocal.append(pt)
            print(pointListLocal)
            holes.append(getHolePt(pointListLocal))
            for i, pt in enumerate(pointListLocal):
                vertices.append([pt[1].x(), pt[1].y()])
                if i > 0:
                    segmList.append([startLen + i - 1, startLen + i])
                if i == len(pointListLocal) - 1:  # also add a cap
                    segmList.append([startLen + i, startLen])
    except:
        try:
            geom = geom.constGet()
            for i in range(geom.numInteriorRings()):
                intRing = geom.interiorRing(i)
                pt_iterator = geom.vertices()
                pointListLocal = []
                startLen = len(vertices)
                for pt in pt_iterator:
                    pointListLocal.append(pt)
                print(pointListLocal)
                holes.append(getHolePt(pointListLocal))
                for i, pt in enumerate(pointListLocal):
                    vertices.append([pt[1].x(), pt[1].y()])
                    if i > 0:
                        segmList.append([startLen + i - 1, startLen + i])
                    if i == len(pointListLocal) - 1:  # also add a cap
                        segmList.append([startLen + i, startLen])
        except:
            pass
    return vertices, segmList, holes


############################

import triangle as tr


shapes = [f.geometry() for f in layer.getFeatures()]
all_polygons = []
for sh in shapes:
    vertices = []
    segments = []
    holes = []
    vertices, segments, holes = getPolyBoundary(sh)
    # print(vertices)
    # print(segments)
    dict_shape = {"vertices": vertices, "segments": segments, "holes": holes}
    t = tr.triangulate(dict_shape, "p")
    # print(t)
    all_polygons.append(t)


print(all_polygons)


########### create Vector layer

height = 0

project = QgsProject.instance()
newName = "new layer"
authid = "EPSG:3857"  # 4326
geomType = "Polygon"

vl = QgsVectorLayer(geomType + "?crs=" + authid, newName, "memory")
# vl.setCrs(crs)
project.addMapLayer(vl, True)

pr = vl.dataProvider()
vl.startEditing()

fets = []
for i in range(len(all_polygons)):
    # pt_list = [QgsPoint(0,0,0), QgsPoint(5,7,0), QgsPoint(1,4,0)]
    pt_list = [QgsPoint(p[0], p[1], height) for p in all_polygons[i]["vertices"]]
    triangle_list = [trg for trg in all_polygons[i]["triangles"]]
    for trg in triangle_list:
        feat = QgsFeature()
        qgsGeom = QgsPolygon()
        polyline = QgsLineString([pt_list[trg[0]], pt_list[trg[1]], pt_list[trg[2]]])
        qgsGeom.setExteriorRing(polyline)
        # qgsGeom.addInteriorRing(QgsLineString())
        feat.setGeometry(qgsGeom)
        fets.append(feat)

r"""
newFields = QgsFields()
for f in layer.features: 
    new_feat = featureToNative(f, newFields)
    if new_feat is not None and new_feat != "": fets.append(new_feat)
    else: logToUser(f"Feature skipped due to invalid geometry", level = 2, func = inspect.stack()[0][3])
# add Layer attribute fields
pr.addAttributes(newFields.toList())
vl.updateFields()
"""
pr.addFeatures(fets)
vl.updateExtents()
vl.commitChanges()
