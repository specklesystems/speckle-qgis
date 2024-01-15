from speckle.converter.geometry.point import (
    applyOffsetsRotation,
    pointToSpeckle,
    transformSpecklePt,
    pointToNativeWithoutTransforms,
    pointToNative,
    applyTransformMatrix,
    scalePointToNative,
)


def test():
    assert 0 == 0


def test_applyOffsetsRotation():
    x = 0
    y = 0
    dataStorage = None
    assert applyOffsetsRotation(x, y, dataStorage) == (None, None)
