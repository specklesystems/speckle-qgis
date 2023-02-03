from typing import List
from specklepy.objects.geometry import Mesh

import shapefile
from shapefile import TRIANGLE_STRIP, TRIANGLE_FAN
from speckle.converter.layers.utils import get_scale_factor
from speckle.logging import logger
from qgis.core import Qgis

def meshToNative(meshes: List[Mesh], path: str):
    """Converts a Speckle Mesh to QgsGeometry"""
    print("06___________________Mesh to Native")
    #print(meshes)
    #print(mesh.units)
    w = shapefile.Writer(path) 
    w.field('speckleTyp', 'C')

    shapes = []
    for geom in meshes:

        if geom.speckle_type =='Objects.Geometry.Mesh' and isinstance(geom, Mesh):
            mesh = geom
            w = fill_mesh_parts(w, mesh)
        else:
            try: 
                if geom.displayValue and isinstance(geom.displayValue, Mesh): 
                    mesh = geom.displayValue
                    w = fill_mesh_parts(w, mesh)
                elif geom.displayValue and isinstance(geom.displayValue, List): 
                    for part in geom.displayValue:
                        if isinstance(part, Mesh): 
                            mesh = part
                            w = fill_mesh_parts(w, mesh)
            except: 
                try: 
                    if geom.displayMesh and isinstance(geom.displayMesh, Mesh): 
                        mesh = geom.displayMesh
                        w = fill_mesh_parts(w, mesh)
                    elif geom.displayMesh and isinstance(geom.displayMesh, List): 
                        for part in geom.displayMesh:
                            if isinstance(part, Mesh): 
                                mesh = part
                                w = fill_mesh_parts(w, mesh)
                except: pass
    w.close()
    return path

def fill_mesh_parts(w: shapefile.Writer, mesh: Mesh):
    scale = get_scale_factor(mesh.units)

    parts_list = []
    types_list = []
    count = 0 # sequence of vertex (not of flat coord list) 
    try:
        #print(len(mesh.faces))
        if len(mesh.faces) % 4 == 0 and (mesh.faces[0] == 0 or mesh.faces[0] == 3):
            for f in mesh.faces:
                try:
                    if mesh.faces[count] == 0 or mesh.faces[count] == 3: # only handle triangles
                        f1 = [ scale*mesh.vertices[mesh.faces[count+1]*3], scale*mesh.vertices[mesh.faces[count+1]*3+1], scale*mesh.vertices[mesh.faces[count+1]*3+2] ]
                        f2 = [ scale*mesh.vertices[mesh.faces[(count+2)]*3], scale*mesh.vertices[mesh.faces[(count+2)]*3+1], scale*mesh.vertices[mesh.faces[(count+2)]*3+2] ]
                        f3 = [ scale*mesh.vertices[mesh.faces[(count+3)]*3], scale*mesh.vertices[mesh.faces[(count+3)]*3+1], scale*mesh.vertices[mesh.faces[(count+3)]*3+2] ]
                        parts_list.append([ f1, f2, f3 ])
                        types_list.append(TRIANGLE_FAN)
                        count += 4
                    else: 
                        count += mesh.faces[count+1]
                        logger.logToUser("Received mesh type is only partially supported", Qgis.Warning)
                except: break
            w.multipatch(parts_list, partTypes=types_list ) # one type for each part
            w.record('displayMesh')
        else: 
            logger.logToUser("Received mesh type is not supported", Qgis.Warning)
            #print("not triangulated mesh")

    except Exception as e: pass #; print(e)
    #print("mesh part written")
    return w
    
def rasterToMesh(vertices, faces, colors):
    mesh = Mesh.create(vertices, faces, colors)
    mesh.units = "m"
    return mesh
