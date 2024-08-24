import inspect
import math
from typing import List, Tuple, Union
from specklepy.objects.geometry import Mesh, Point
from specklepy.objects.other import RenderMaterial

import shapefile
from shapefile import OUTER_RING
from speckle.converter.geometry.point import (
    pointToNative,
)
from speckle.converter.geometry.utils import (
    apply_pt_transform_matrix,
    fix_orientation,
    projectToPolygon,
    triangulatePolygon,
    transform_speckle_pt_on_receive,
)
from speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.converter.layers.utils import (
    getDisplayValueList,
)
from plugin_utils.helpers import get_scale_factor


from speckle.utils.panel_logging import logToUser

try:
    from qgis.core import (
        QgsMultiPolygon,
        QgsPolygon,
        QgsLineString,
        QgsFeature,
        QgsVectorLayer,
    )
except ModuleNotFoundError:
    pass


def deconstructSpeckleMesh(mesh: Mesh, dataStorage):
    try:
        scale = get_scale_factor(mesh.units, dataStorage)
        parts_list = []
        types_list = []

        count = 0  # sequence of vertex (not of flat coord list)
        for f in mesh.faces:  # real number of loops will be at least 3 times less
            try:
                vertices = mesh.faces[count]
                if mesh.faces[count] == 0:
                    vertices = 3
                if mesh.faces[count] == 1:
                    vertices = 4

                face = []
                for i in range(vertices):
                    index_faces = count + 1 + i
                    index_vertices = mesh.faces[index_faces] * 3

                    pt = Point(
                        x=mesh.vertices[index_vertices],
                        y=mesh.vertices[index_vertices + 1],
                        z=mesh.vertices[index_vertices + 2],
                        units="m",
                    )
                    pt = apply_pt_transform_matrix(pt, dataStorage)
                    face.append([scale * pt.x, scale * pt.y, scale * pt.z])

                parts_list.append(face)
                types_list.append(OUTER_RING)
                count += vertices + 1
            except:
                break  # when out of range

        return parts_list, types_list
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return [], []


def fill_multi_mesh_parts(
    w: shapefile.Writer, meshes: List[Mesh], geom_id: str, dataStorage
):
    try:
        parts_list = []
        types_list = []
        for mesh in meshes:
            if not isinstance(mesh, Mesh):
                continue
            try:
                parts_list_x, types_list_x = deconstructSpeckleMesh(mesh, dataStorage)
                for i, face in enumerate(parts_list_x):
                    for k, p in enumerate(face):
                        pt = Point(x=p[0], y=p[1], z=p[2], units=mesh.units)
                        pt = transform_speckle_pt_on_receive(pt, dataStorage)
                        parts_list_x[i][k] = [pt.x, pt.y, pt.z]
                parts_list.extend(parts_list_x)
                types_list.extend(types_list_x)
            except Exception as e:
                print(e)

        w.multipatch(parts_list, partTypes=types_list)  # one type for each part
        w.record(geom_id)
        return w
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def writeMeshToShp(meshes: List[Mesh], path: str, dataStorage):
    """Converts a Speckle Mesh to QgsGeometry"""
    try:
        try:
            w = shapefile.Writer(path)
        except Exception as e:
            logToUser(e)
            return

        w.field("speckle_id", "C")

        for _, geom in enumerate(meshes):
            meshList: List = getDisplayValueList(geom)
            w = fill_multi_mesh_parts(w, meshList, geom.id, dataStorage)
        w.close()
        return path

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def fill_mesh_parts(w: shapefile.Writer, mesh: Mesh, geom_id: str, dataStorage):
    try:
        parts_list, types_list = deconstructSpeckleMesh(mesh, dataStorage)
        for i, face in enumerate(parts_list):
            for k, p in enumerate(face):
                pt = Point(x=p[0], y=p[1], z=p[2], units=mesh.units)
                pt = transform_speckle_pt_on_receive(pt, dataStorage)
                parts_list[i][k] = [pt.x, pt.y, pt.z]
        w.multipatch(parts_list, partTypes=types_list)  # one type for each part
        w.record(geom_id)

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])

    return w


def constructMeshFromRaster(
    vertices: List[Union[float, int]],
    faces: List[int],
    colors: Union[List[int], None],
    dataStorage,
):
    try:
        if vertices is None or faces is None:
            return None
        mesh = Mesh.create(vertices, faces, colors)
        mesh.units = "m"
        return mesh
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def constructMesh(
    vertices: List[Union[float, int]], faces: List[int], colors: List[int], dataStorage
):
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
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def meshPartsFromPolygon(
    polyBorder: List[Point],
    voidsAsPts: List[List[Point]],
    existing_vert: int,
    feature: "QgsFeature",
    feature_geom,
    layer: "QgsVectorLayer",
    height,
    dataStorage,
    xform=None,
) -> Tuple[
    Union[int, None],
    Union[List[float], None],
    Union[List[int], None],
    Union[List[int], None],
    Union[int, None],
]:
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
        if len(polyBorder) >= maxPoints:
            coef = math.floor(len(polyBorder) / maxPoints)
            iterations = 1

        if len(polyBorder) < 3:
            return None, None, None, None, None

        col = featureColorfromNativeRenderer(feature, layer)

        universal_z_value = polyBorder[0].z

        vertices3d_original_tuples = [
            [polyBorder[coef * i].x, polyBorder[coef * i].y, polyBorder[coef * i].z]
            for i, p in enumerate(polyBorder)
            if coef * i < len(polyBorder)
        ]
        holes3d_tuples = [
            [
                [p[coef * i].x, p[coef * i].y, p[coef * i].z]
                for i, v in enumerate(p)
                if coef * i < len(p)
            ]
            for p in voidsAsPts
        ]
        # height_set = list(set([p[2] for p in vertices3d_original_tuples]))

        vertices3d_original = [
            item for sub_list in vertices3d_original_tuples for item in sub_list
        ]

        vertices3d = vertices3d_original.copy()
        vertices3d_tuples = vertices3d_original_tuples.copy()
        hole_indices = []

        for hole_tuple_list in holes3d_tuples:
            current_count = int(len(vertices3d) / 3)
            hole_indices.append(current_count)
            vertices3d.extend(item for sub_list in hole_tuple_list for item in sub_list)
            vertices3d_tuples.extend(hole_tuple_list)

        # get points from original geometry #################################
        triangle_list = []

        # triangles are normally returned counter-clockwise: face looking up
        # floor: need positive - clockwise (looking down); cap need negative (counter-clockwise)
        triangle_list = triangulatePolygon(
            vertices3d,
            hole_indices,
            3,
            dataStorage,
            coef,
            xform,
        )

        try:
            if len(triangle_list) == 0:  # triangulation not successful
                vert_count = len(vertices3d_tuples)
                vertices.extend(vertices3d)
                faces.extend([vert_count] + list(range(vert_count)))

                total_vertices += vert_count
                ran = range(0, total_vertices)

                logToUser(
                    "Vertical or invalid polygon, display Mesh will be approximated from the boundary",
                    level=1,
                    func=inspect.stack()[0][3],
                )

            # if triangulated:
            for trg in triangle_list:
                a = trg[0]
                b = trg[1]
                c = trg[2]

                # if extruded, face down (make clockwise)
                if height is not None:
                    a = trg[2]
                    b = trg[1]
                    c = trg[0]

                vertices.extend(
                    vertices3d_tuples[a] + vertices3d_tuples[b] + vertices3d_tuples[c]
                )
                total_vertices += 3
                # all faces are counter-clockwise now
                if height is None:
                    faces.extend(
                        [
                            3,
                            total_vertices - 3,
                            total_vertices - 2,
                            total_vertices - 1,
                        ]
                    )
                else:  # if extruding
                    faces.extend(
                        [
                            3,
                            total_vertices - 1,
                            total_vertices - 2,
                            total_vertices - 3,
                        ]
                    )  # reverse to clock-wise (facing down)

            ran = range(0, total_vertices)
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])

        # a cap ##################################
        if len(vertices) == 0:
            logToUser(
                "Polygon Mesh was not created", level=2, func=inspect.stack()[0][3]
            )
            return None, None, None, None, None

        if height is not None:
            # change the pt list to height
            pt_list = [
                [p[0], p[1], universal_z_value + height] for p in vertices3d_tuples
            ]

            for trg in triangle_list:
                a = trg[0]
                b = trg[1]
                c = trg[2]
                # all faces are counter-clockwise still
                vertices.extend(pt_list[a] + pt_list[b] + pt_list[c])
                total_vertices += 3
                faces_cap.extend(
                    [3, total_vertices - 3, total_vertices - 2, total_vertices - 1]
                )

            ###################################### add extrusions
            polyBorder = fix_orientation(polyBorder, True, coef)  # clockwise
            universal_z_value = polyBorder[0].z
            for k, pt in enumerate(polyBorder):
                try:
                    vertices_side.extend(
                        [
                            polyBorder[k].x,
                            polyBorder[k].y,
                            universal_z_value,
                            polyBorder[k].x,
                            polyBorder[k].y,
                            height + universal_z_value,
                            polyBorder[k + 1].x,
                            polyBorder[k + 1].y,
                            height + universal_z_value,
                            polyBorder[k + 1].x,
                            polyBorder[k + 1].y,
                            universal_z_value,
                        ]
                    )
                    faces_side.extend(
                        [
                            4,
                            total_vertices,
                            total_vertices + 1,
                            total_vertices + 2,
                            total_vertices + 3,
                        ]
                    )
                    total_vertices += 4

                except:
                    vertices_side.extend(
                        [
                            polyBorder[k].x,
                            polyBorder[k].y,
                            universal_z_value,
                            polyBorder[k].x,
                            polyBorder[k].y,
                            height + universal_z_value,
                            polyBorder[0].x,
                            polyBorder[0].y,
                            height + universal_z_value,
                            polyBorder[0].x,
                            polyBorder[0].y,
                            universal_z_value,
                        ]
                    )
                    faces_side.extend(
                        [
                            4,
                            total_vertices,
                            total_vertices + 1,
                            total_vertices + 2,
                            total_vertices + 3,
                        ]
                    )
                    total_vertices += 4

                    break

            for v in voidsAsPts:  # already at the correct hight (even projected)
                v = fix_orientation(v, False, coef)  # counter-clockwise
                for k, pt in enumerate(v):
                    void = []
                    try:
                        vertices_side.extend(
                            [
                                v[k].x,
                                v[k].y,
                                universal_z_value,
                                v[k].x,
                                v[k].y,
                                height + universal_z_value,
                                v[k + 1].x,
                                v[k + 1].y,
                                height + universal_z_value,
                                v[k + 1].x,
                                v[k + 1].y,
                                universal_z_value,
                            ]
                        )
                        faces_side.extend(
                            [
                                4,
                                total_vertices,
                                total_vertices + 1,
                                total_vertices + 2,
                                total_vertices + 3,
                            ]
                        )
                        total_vertices += 4

                    except:
                        vertices_side.extend(
                            [
                                v[k].x,
                                v[k].y,
                                universal_z_value,
                                v[k].x,
                                v[k].y,
                                height + universal_z_value,
                                v[0].x,
                                v[0].y,
                                height + universal_z_value,
                                v[0].x,
                                v[0].y,
                                universal_z_value,
                            ]
                        )
                        faces_side.extend(
                            [
                                4,
                                total_vertices,
                                total_vertices + 1,
                                total_vertices + 2,
                                total_vertices + 3,
                            ]
                        )
                        total_vertices += 4

                        break

            ############################################

            ran = range(0, total_vertices)
            colors = [col for i in ran]  # apply same color for all vertices
            return (
                total_vertices,
                vertices + vertices_cap + vertices_side,
                faces + faces_cap + faces_side,
                colors,
                iterations,
            )

        else:
            ran = range(0, total_vertices)
            colors = [col for i in ran]  # apply same color for all vertices

            return total_vertices, vertices, faces, colors, iterations

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None, None, None, None


def meshToNative(meshes: List[Mesh], dataStorage) -> "QgsMultiPolygon":
    try:
        multiPolygon = QgsMultiPolygon()
        for mesh in meshes:
            parts_list, types_list = deconstructSpeckleMesh(mesh, dataStorage)
            for part in parts_list:
                polygon = QgsPolygon()
                units = dataStorage.currentUnits
                if not isinstance(units, str):
                    units = "m"
                pts = [Point(x=pt[0], y=pt[1], z=pt[2], units=units) for pt in part]
                pts.append(pts[0])
                boundary = QgsLineString([pointToNative(pt, dataStorage) for pt in pts])
                polygon.setExteriorRing(boundary)

                if polygon is not None:
                    multiPolygon.addGeometry(polygon)
        return multiPolygon
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None
