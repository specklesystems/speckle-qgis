r"""
from speckle.converter.geometry.point import (
    pointToSpeckle,
    transformSpecklePt,
    pointToNativeWithoutTransforms,
    pointToNative,
    applyTransformMatrix,
    scalePointToNative,
)

def test_applyOffsetsRotation():
    x = 0
    y = 0
    dataStorage = None
    assert applyOffsetsRotation(x, y, dataStorage) == (None, None)

"""


def test():
    assert 0 == 0
