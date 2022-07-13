from typing import List
from specklepy.objects.geometry import Mesh


def meshToNative(mesh: Mesh):
    """Converts a Speckle Mesh to QgsGeometry. Currently UNSUPPORTED"""
    return None


def rasterToMesh(vertices: List[float], faces: List[int], colors: List[int]):
    mesh = Mesh.create(vertices, faces, colors)
    return mesh
