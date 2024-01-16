from speckle.converter.geometry.mesh import (
    deconstructSpeckleMesh,
    fill_multi_mesh_parts,
    writeMeshToShp,
    fill_mesh_parts,
    constructMeshFromRaster,
    constructMesh,
)
import inspect
from typing import List, Tuple
import pathlib

import shapefile
from specklepy.objects.geometry import Mesh, Point
from specklepy.objects.other import RenderMaterial


def test_deconstructSpeckleMesh(mesh, data_storage):
    result = deconstructSpeckleMesh(mesh, data_storage)
    assert isinstance(result, Tuple)
    assert len(result) == 2
    assert isinstance(result[0], list) and isinstance(result[1], list)


def test_fill_multi_mesh_parts(mesh, data_storage):
    path = pathlib.Path(__file__).parent.resolve()
    w = shapefile.Writer(path)
    w.field("speckle_id", "C")
    meshes = [mesh]
    geom_id = "20"
    result = fill_multi_mesh_parts(w, meshes, geom_id, data_storage)
    assert isinstance(result, shapefile.Writer)


def test_writeMeshToShp(mesh, data_storage):
    path = pathlib.Path(__file__).parent.resolve().__str__()
    meshes = [mesh]
    result = writeMeshToShp(meshes, path, data_storage)
    assert result == path


def test_fill_mesh_parts(mesh, data_storage):
    path = pathlib.Path(__file__).parent.resolve().__str__()
    w = shapefile.Writer(path)
    w.field("speckle_id", "C")
    geom_id = "20"
    result = fill_mesh_parts(w, mesh, geom_id, data_storage)
    assert isinstance(result, shapefile.Writer)


def test_constructMeshFromRaster(data_storage):
    vertices = [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]
    faces = [4, 0, 1, 2, 3]
    colors = None
    result = constructMeshFromRaster(vertices, faces, colors, data_storage)
    assert isinstance(result, Mesh)
    assert isinstance(result.vertices, list)
    assert len(result.vertices) == len(vertices)


def test_constructMesh(data_storage):
    vertices = [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]
    faces = [4, 0, 1, 2, 3]
    colors = [0, 0, 0, 0]
    result = constructMesh(vertices, faces, colors, data_storage)
    assert isinstance(result, Mesh)
    assert isinstance(result.vertices, list)
    assert len(result.vertices) == len(vertices)
    assert hasattr(result, "renderMaterial")
    assert result["renderMaterial"]["diffuse"] == colors[0]
