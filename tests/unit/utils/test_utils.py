from speckle.utils.utils import get_qgis_python_path


def test_get_qgis_python_path():
    result = get_qgis_python_path()
    assert isinstance(result, str)
