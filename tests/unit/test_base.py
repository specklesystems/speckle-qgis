import pytest
from specklepy.objects.base import Base


def test_speckle_type_cannot_be_set(base: Base) -> None:
    assert base.speckle_type == "Base"
    base.speckle_type = "unset"
    assert base.speckle_type == "Base"
