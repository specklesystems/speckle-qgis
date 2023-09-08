import inspect
import math
import time
from typing import List
from specklepy.objects.geometry import Mesh, Point
from specklepy.objects.other import RenderMaterial

import shapefile
from shapefile import TRIANGLE_STRIP, TRIANGLE_FAN, OUTER_RING
from speckle.converter.geometry.point import applyTransformMatrix, pointToNative, pointToNativeWithoutTransforms, scalePointToNative, transformSpecklePt
from speckle.converter.geometry.utils import fix_orientation, projectToPolygon, triangulatePolygon
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.converter.layers.utils import get_scale_factor, get_scale_factor_to_meter, getDisplayValueList
#from speckle.utils.panel_logging import logger
from speckle.utils.panel_logging import logToUser

from qgis.core import (
    Qgis, QgsPoint, QgsPointXY, QgsMultiPolygon, QgsPolygon, QgsLineString, QgsFeature, QgsVectorLayer
    )
#from panda3d.core import Triangulator

def meshToNative(meshes: List[Mesh], dataStorage) -> QgsMultiPolygon:
    try:
        multiPolygon = QgsMultiPolygon()
        for mesh in meshes:
            parts_list, types_list = deconstructSpeckleMesh(mesh, dataStorage)
            for part in parts_list: 
                polygon = QgsPolygon()
                pts = [Point(x=pt[0], y=pt[1], z=pt[2], units="m") for pt in part]
                pts.append(pts[0])
                boundary = QgsLineString([pointToNative(pt, dataStorage) for pt in pts])
                polygon.setExteriorRing(boundary)

                if polygon is not None:
                    multiPolygon.addGeometry(polygon)
        return multiPolygon
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None
    
def writeMeshToShp(meshes: List, path: str, dataStorage):
    """Converts a Speckle Mesh to QgsGeometry"""
    try:
        #print("06___________________writeMeshToShp")

        try:
            w = shapefile.Writer(path) 
        except Exception as e: 
            logToUser(e)
            return 
        #print(w)
        w.field('speckle_id', 'C')

        shapes = []
        #print(meshes)
        for i, geom in enumerate(meshes):

            meshList: List = getDisplayValueList(geom)
            #print(geom)
            w = fill_multi_mesh_parts(w, meshList, geom.id, dataStorage)

            r'''
            if geom.speckle_type =='Objects.Geometry.Mesh' and isinstance(geom, Mesh):
                mesh = geom
                w = fill_mesh_parts(w, mesh, geom.id, dataStorage)
            else:
                try: 
                    if geom.displayValue and isinstance(geom.displayValue, Mesh): 
                        mesh = geom.displayValue
                        w = fill_mesh_parts(w, mesh, geom.id, dataStorage)
                    elif geom.displayValue and isinstance(geom.displayValue, List): 
                        print("__ this should be a common case")
                        w = fill_multi_mesh_parts(w, geom.displayValue, geom.id, dataStorage)
                except: 
                    try: 
                        if geom["@displayValue"] and isinstance(geom["@displayValue"], Mesh): 
                            mesh = geom["@displayValue"]
                            w = fill_mesh_parts(w, mesh, geom.id, dataStorage)
                        elif geom["@displayValue"] and isinstance(geom["@displayValue"], List): 
                            w = fill_multi_mesh_parts(w, geom["@displayValue"], geom.id, dataStorage)
                    except:
                        try: 
                            if geom.displayMesh and isinstance(geom.displayMesh, Mesh): 
                                mesh = geom.displayMesh
                                w = fill_mesh_parts(w, mesh, geom.id, dataStorage)
                            elif geom.displayMesh and isinstance(geom.displayMesh, List): 
                                w = fill_multi_mesh_parts(w, geom.displayMesh, geom.id, dataStorage)
                        except: pass
            ''' 
        w.close()
        #print("06-end___________________Mesh to Native")
        return path
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def fill_multi_mesh_parts(w: shapefile.Writer, meshes: List[Mesh], geom_id: str, dataStorage):
    
    #print("07___________________fill_multi_mesh_parts")
    try:
        parts_list = []
        types_list = []
        for mesh in meshes:
            if not isinstance(mesh, Mesh): continue
            try:
                #print(f"Fill multi-mesh parts # {geom_id}")
                parts_list_x, types_list_x = deconstructSpeckleMesh(mesh, dataStorage) 
                for i, face in enumerate(parts_list_x):
                    for k, p in enumerate(face):
                        pt = Point(x = p[0], y= p[1], z = p[2], units = mesh.units)
                        pt = transformSpecklePt(pt, dataStorage)
                        parts_list_x[i][k] = [pt.x, pt.y, pt.z]
                parts_list.extend(parts_list_x)
                types_list.extend(types_list_x)
            except Exception as e: print(e) 
        
        w.multipatch(parts_list, partTypes=types_list ) # one type for each part
        w.record(geom_id)
        #print("07-end___________________fill_multi_mesh_parts")
        return w
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def fill_mesh_parts(w: shapefile.Writer, mesh: Mesh, geom_id: str, dataStorage):
    
    try:
        parts_list, types_list = deconstructSpeckleMesh(mesh, dataStorage) 
        for i, face in enumerate(parts_list):
            for k, p in enumerate(face):
                pt = Point(x = p[0], y= p[1], z = p[2], units = mesh.units)
                pt = transformSpecklePt(pt, dataStorage)
                parts_list[i][k] = [pt.x, pt.y, pt.z]
        w.multipatch(parts_list, partTypes=types_list ) # one type for each part
        w.record(geom_id)

    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])

    return w

def deconstructSpeckleMesh(mesh: Mesh, dataStorage):
    
    #print("deconstructSpeckleMesh")
    try:
        scale = get_scale_factor(mesh.units, dataStorage)
        parts_list = []
        types_list = []

        count = 0 # sequence of vertex (not of flat coord list) 
        for f in mesh.faces: # real number of loops will be at least 3 times less 
            try:
                vertices = mesh.faces[count]
                if mesh.faces[count] == 0: vertices = 3
                if mesh.faces[count] == 1: vertices = 4
                
                face = []
                for i in range(vertices):
                    index_faces = count + 1 + i 
                    index_vertices = mesh.faces[index_faces]*3
                    
                    pt = Point(x = mesh.vertices[index_vertices], y = mesh.vertices[index_vertices+1], z = mesh.vertices[index_vertices+2], units = "m")
                    pt = applyTransformMatrix(pt, dataStorage)
                    face.append([ scale * pt.x, scale * pt.y, scale * pt.z ]) 

                parts_list.append(face)
                types_list.append(OUTER_RING)
                count += vertices + 1
            except: break # when out of range 

        #print("end-deconstructSpeckleMesh")
        return parts_list, types_list
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return [],[]

def constructMeshFromRaster(vertices, faces, colors, dataStorage):
    try:
        mesh = Mesh.create(vertices, faces, colors)
        mesh.units = "m"
        return mesh
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def constructMesh(vertices, faces, colors, dataStorage):
    try:
        if vertices is None or faces is None or colors is None:
            return None
        mesh = Mesh.create(vertices, faces, colors)
        mesh.units = "m"
        material = RenderMaterial()
        material.diffuse = colors[0]
        material.name = str(colors[0])
        mesh.renderMaterial = material 
        return mesh
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None

def meshPartsFromPolygon(polyBorder: List[Point], voidsAsPts: List[List[Point]], existing_vert: int, feature: QgsFeature, feature_geom, layer: QgsVectorLayer, height, dataStorage):
    try:
        faces = []
        faces_cap = []
        faces_side = []

        vertices = []
        vertices_cap = []
        vertices_side = []

        total_vertices = 0
        iterations = 0

        coef = 1
        maxPoints = 5000
        if len(polyBorder) >= maxPoints: coef = int(len(polyBorder)/maxPoints)

        col = featureColorfromNativeRenderer(feature, layer)
            
        if len(voidsAsPts) == 0: # only if there is a mesh with no voids and large amount of points
            # floor: need positive - clockwise (looking down); cap need negative (counter-clockwise)
            polyBorder = fix_orientation(polyBorder, True, coef) # clockwise

            if height is None: polyBorder.reverse() # when no extrusions: face up, counter-clockwise

            for k, ptt in enumerate(polyBorder): #pointList:
                pt = polyBorder[k*coef]
                if k < maxPoints:
                    vertices.extend([pt.x, pt.y, pt.z])
                    total_vertices += 1
                else: break

            ran = range(0, total_vertices)
            faces = [total_vertices]
            faces.extend([i + existing_vert for i in ran])

            # a cap
            ##################################
            if height is not None:
                ran = range(total_vertices, 2*total_vertices)
                faces.append(total_vertices) 
                faces2 = [i + existing_vert for i in ran]
                faces2.reverse()
                faces.extend(faces2) 

                vertices_copy = vertices.copy()
                count = 0
                for item in vertices_copy:
                    try: 
                        vertices.extend([vertices_copy[count], vertices_copy[count+1], vertices_copy[count+2] + height])
                        count += 3 
                    except: break 
                total_vertices *= 2
                
                ###################################### add extrusions
                universal_z_value = polyBorder[0].z
                for k, pt in enumerate(polyBorder):
                    polyBorder2 = []
                    try:
                        vertices_side.extend([polyBorder[k].x, polyBorder[k].y, universal_z_value,
                                         polyBorder[k].x, polyBorder[k].y, height + universal_z_value,
                                         polyBorder[k+1].x, polyBorder[k+1].y, height + universal_z_value,
                                         polyBorder[k+1].x, polyBorder[k+1].y, universal_z_value])
                        faces_side.extend([4, total_vertices, total_vertices+1,total_vertices+2,total_vertices+3])
                        total_vertices +=4

                    except: 
                        vertices_side.extend([polyBorder[k].x, polyBorder[k].y, universal_z_value,
                                         polyBorder[k].x, polyBorder[k].y, height + universal_z_value,
                                         polyBorder[0].x, polyBorder[0].y, height + universal_z_value,
                                         polyBorder[0].x, polyBorder[0].y, universal_z_value])
                        faces_side.extend([4, total_vertices, total_vertices+1,total_vertices+2,total_vertices+3])
                        total_vertices +=4

                        break
                
                ran = range(0, total_vertices)
                colors = [col for i in ran] # apply same color for all vertices
                return total_vertices, vertices + vertices_side, faces + faces_side, colors, iterations
                ######################################
            else:
                colors = [col for i in ran] # apply same color for all vertices
                return total_vertices, vertices, faces, colors, iterations

        else: # if there are voids: face should be clockwise 
            # if its a large polygon with voids to be triangualted, lower the coef even more:
            #maxPoints = 100
            if len(polyBorder) >= maxPoints: coef = int(len(polyBorder)/maxPoints)

            universal_z_value = polyBorder[0].z 
            
            # get points from original geometry #################################
            triangulated_geom, vertices3d_original, iterations = triangulatePolygon(feature_geom, dataStorage)
            
            # temporary solution, as the list of points is not the same anymore:
            if triangulated_geom is None or vertices3d_original is None:
                return None, None, None, None, None  
            
            vertices3d = []
            for v in triangulated_geom['vertices']:
                vertices3d.append(v+[0.0])
            # get substitute value for missing z-val
            existing_3d_pts = []
            for i, p in enumerate(vertices3d): 
                if p[2] is not None and str(p[2])!="" and str(p[2]).lower()!="nan" and p[2] != universal_z_value: # only from boundary 
                    p[2] += universal_z_value 
                    existing_3d_pts.append(p)
                    if len(existing_3d_pts) == 3: break
            pt_list = []
            for i, p in enumerate(triangulated_geom['vertices']): 
                z_val = vertices3d[i][2]
                if z_val is None or str(z_val)!="" or str(z_val).lower()!="nan": 
                    #    #z_val = any_existing_z
                    if len(existing_3d_pts)>=3:
                        z_val = projectToPolygon(vertices3d[i], existing_3d_pts)
                    else: 
                        z_val = universal_z_value
                pt_list.append( [p[0], p[1], z_val ] ) 

            triangle_list = [ trg for trg in triangulated_geom['triangles']]
            
            try:
                for trg in triangle_list:
                    a = trg[0]
                    b = trg[1]
                    c = trg[2]
                    vertices.extend(pt_list[a] + pt_list[b] + pt_list[c])
                    total_vertices += 3
                    # all faces are counter-clockwise now
                    if height is None:
                        faces.extend([3, total_vertices-3, total_vertices-2, total_vertices-1])
                    else: # if extruding
                        faces.extend([3, total_vertices-1, total_vertices-2, total_vertices-3]) # reverse to clock-wise (facing down)
                    
                ran = range(0, total_vertices)
            except Exception as e:
                logToUser(e, level = 2, func = inspect.stack()[0][3])
            
            # a cap ##################################
            if height is not None:
                # change the pt list to height 
                pt_list = [ [p[0], p[1], universal_z_value + height] for p in triangulated_geom['vertices']]
                
                for trg in triangle_list: 
                    a = trg[0]
                    b = trg[1]
                    c = trg[2]
                    # all faces are counter-clockwise now
                    vertices.extend(pt_list[a] + pt_list[b] + pt_list[c])
                    total_vertices += 3
                    faces_cap.extend([3, total_vertices-3, total_vertices-2, total_vertices-1]) 

                ###################################### add extrusions
                polyBorder = fix_orientation(polyBorder, True, coef) # clockwise
                universal_z_value = polyBorder[0].z
                for k, pt in enumerate(polyBorder):
                    try:
                        vertices_side.extend([polyBorder[k].x, polyBorder[k].y, universal_z_value,
                                         polyBorder[k].x, polyBorder[k].y, height + universal_z_value,
                                         polyBorder[k+1].x, polyBorder[k+1].y, height + universal_z_value,
                                         polyBorder[k+1].x, polyBorder[k+1].y, universal_z_value])
                        faces_side.extend([4, total_vertices, total_vertices+1,total_vertices+2,total_vertices+3])
                        total_vertices +=4

                    except: 
                        vertices_side.extend([polyBorder[k].x, polyBorder[k].y, universal_z_value,
                                         polyBorder[k].x, polyBorder[k].y, height + universal_z_value,
                                         polyBorder[0].x, polyBorder[0].y, height + universal_z_value,
                                         polyBorder[0].x, polyBorder[0].y, universal_z_value])
                        faces_side.extend([4, total_vertices, total_vertices+1,total_vertices+2,total_vertices+3])
                        total_vertices +=4

                        break

                for v in voidsAsPts: # already at the correct hight (even projected) 
                    v = fix_orientation(v, False, coef) # counter-clockwise
                    for k, pt in enumerate(v):
                        void =[]
                        try:
                            vertices_side.extend([v[k].x, v[k].y, universal_z_value,
                                            v[k].x, v[k].y, height + universal_z_value,
                                            v[k+1].x, v[k+1].y, height + universal_z_value,
                                            v[k+1].x, v[k+1].y, universal_z_value])
                            faces_side.extend([4, total_vertices, total_vertices+1,total_vertices+2,total_vertices+3])
                            total_vertices +=4
 
                        except:
                            vertices_side.extend([v[k].x, v[k].y, universal_z_value,
                                            v[k].x, v[k].y, height + universal_z_value,
                                            v[0].x, v[0].y, height + universal_z_value,
                                            v[0].x, v[0].y, universal_z_value])
                            faces_side.extend([4, total_vertices, total_vertices+1,total_vertices+2,total_vertices+3])
                            total_vertices +=4

                            break
                            
                ############################################

                ran = range(0, total_vertices)
                colors = [col for i in ran] # apply same color for all vertices
                return total_vertices, vertices + vertices_cap + vertices_side, faces + faces_cap + faces_side, colors, iterations
                
            else: 
                ran = range(0, total_vertices)
                colors = [col for i in ran] # apply same color for all vertices
                
                return total_vertices, vertices, faces, colors, iterations

            
    
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return None, None, None, None, None