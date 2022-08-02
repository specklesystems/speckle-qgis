from specklepy.objects.geometry import Mesh


def meshToNative(mesh: Mesh):
    """Converts a Speckle Mesh to QgsGeometry. Currently UNSUPPORTED"""
    return None

def rasterToMesh(vertices, faces, colors):
    mesh = Mesh.create(vertices, faces, colors)
    mesh.units = "m"
    return mesh
