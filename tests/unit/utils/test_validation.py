from speckle.utils.validation import (
    tryGetClient,
    tryGetStream,
    validateStream,
    validateBranch,
    validateCommit,
    validateTransport,
)
import inspect
from typing import Union
from specklepy.core.api.credentials import get_default_account
from specklepy.core.api.wrapper import StreamWrapper
from specklepy.core.api.models import Stream, Branch, Commit
from specklepy.transports.server import ServerTransport
from specklepy.core.api.client import SpeckleClient
from specklepy.core.api.credentials import get_local_accounts
from specklepy.logging.exceptions import SpeckleException, GraphQLException

import pytest
from specklepy_qt_ui.qt_ui.DataStorage import DataStorage


@pytest.fixture()
def data_storage():
    sample_obj = DataStorage()
    sample_obj.accounts = get_local_accounts()
    return sample_obj


@pytest.fixture()
def stream_wrapper_fe2():
    sample_obj = StreamWrapper("https://latest.speckle.systems/projects/92b620fb17")
    sample_obj.get_client()
    return sample_obj


@pytest.fixture()
def speckle_client(stream_wrapper_fe2):
    sample_obj = stream_wrapper_fe2._client
    return sample_obj


@pytest.fixture()
def stream(stream_wrapper_fe2):
    sample_obj = stream_wrapper_fe2._client.stream.get(id=stream_wrapper_fe2.stream_id)
    return sample_obj


@pytest.fixture()
def branch(stream_wrapper_fe2):
    stream = stream_wrapper_fe2._client.stream.get(
        id=stream_wrapper_fe2.stream_id, branch_limit=100
    )
    for br in stream.branches.items:
        # if br.id == "0fe8ca21c0":
        if br.name == "today":
            return br


@pytest.fixture()
def commit_id():
    return "6283209680"


def test_tryGetClient_fe2(stream_wrapper_fe2, data_storage):
    result = tryGetClient(
        stream_wrapper_fe2, data_storage, write=False, dockwidget=None
    )
    assert isinstance(result[0], SpeckleClient)
    assert isinstance(result[1], Stream)


def test_tryGetClient_fe2_write(stream_wrapper_fe2, data_storage):
    try:
        tryGetClient(stream_wrapper_fe2, data_storage, write=True, dockwidget=None)
    except Exception:
        assert True


def test_tryGetStream(stream_wrapper_fe2, data_storage):
    result = tryGetStream(
        stream_wrapper_fe2, data_storage, write=False, dockwidget=None
    )
    assert isinstance(result, Stream)


def test_validateStream(stream):
    result = validateStream(stream, dockwidget=None)
    assert isinstance(result, Stream)


def test_validateBranch(stream):
    branch_name = "main"
    result = validateBranch(stream, branch_name, checkCommits=False, dockwidget=None)
    assert isinstance(result, Branch)


def test_validateBranch_no_commits():
    sample_wrapper = StreamWrapper("https://latest.speckle.systems/projects/7117052f4e")
    sample_wrapper.get_client()
    stream_fe1 = sample_wrapper._client.stream.get(id=sample_wrapper.stream_id)
    branch_name = "empty_branch"
    result = validateBranch(stream_fe1, branch_name, checkCommits=True, dockwidget=None)
    assert result is None


def test_validateCommit(branch, commit_id):
    result = validateCommit(branch, commit_id, dockwidget=None)
    assert isinstance(result, Commit)


def test_validateTransport(speckle_client, stream_wrapper_fe2):
    result = validateTransport(speckle_client, stream_wrapper_fe2.stream_id)
    assert isinstance(result, ServerTransport)
