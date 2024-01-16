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

