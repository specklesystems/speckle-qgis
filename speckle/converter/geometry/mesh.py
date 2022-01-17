from specklepy.objects.geometry import Mesh


def meshToNative(mesh: Mesh):
    """Converts a Speckle Mesh to QgsGeometry. Currently UNSUPPORTED"""
    return None

def rasterToMesh(vertices, faces, colors):
    mesh = Mesh()
    mesh.vertices = vertices
    mesh.faces = faces
    mesh.colors = colors
    return mesh