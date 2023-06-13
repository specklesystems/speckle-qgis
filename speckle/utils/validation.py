
import inspect
from typing import Union
from specklepy.api.wrapper import StreamWrapper
from specklepy.api.models import Stream, Branch, Commit 
from specklepy.transports.server import ServerTransport
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException, GraphQLException

from speckle.utils.panel_logging import logger
from qgis.core import Qgis
from pyqt_ui.logger import logToUser
  
def tryGetStream (sw: StreamWrapper) -> Stream:
    try:
        client = sw.get_client()
        stream = client.stream.get(id = sw.stream_id, branch_limit = 100, commit_limit = 100)
        if isinstance(stream, GraphQLException):
            raise SpeckleException(stream.errors[0]['message'])
        return stream
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3])
        return

def validateStream(streamWrapper: StreamWrapper, dockwidget) -> Union[Stream, None]:
    try: 
        stream = tryGetStream(streamWrapper)

        if isinstance(stream, SpeckleException): return None

        if stream.branches is None:
            logToUser("Stream has no branches", level = 1, plugin = dockwidget)
            return None
        return stream
    except Exception as e:
        logToUser(e, level = 2, plugin = dockwidget)
        return

def validateBranch(stream: Stream, branchName: str, checkCommits: bool, dockwidget) ->  Union[Branch, None]:
    try:
        branch = None
        if not stream.branches or not stream.branches.items: 
            return None
        for b in stream.branches.items:
            if b.name == branchName:
                branch = b
                break
        if branch is None: 
            logToUser("Failed to find a branch", level = 2, plugin = dockwidget)
            return None
        if checkCommits == True:
            if branch.commits is None:
                logToUser("Failed to find a branch", level = 2, plugin = dockwidget)
                return None
            if len(branch.commits.items)==0:
                logToUser("Branch contains no commits", level = 1, plugin = dockwidget)
                return None
        return branch
    except Exception as e:
        logToUser(e, level = 2, plugin = dockwidget)
        return
            
def validateCommit(branch: Branch, commitId: str, dockwidget = None) -> Union[Commit, None]:
    try:
        commit = None
        try: commitId = commitId.split(" | ")[0]
        except: logToUser("Commit ID is not valid", level = 2, plugin = dockwidget)

        if commitId.startswith("Latest") and len(branch.commits.items)>0:
            commit = branch.commits.items[0]
        else:
            for i in branch.commits.items:
                if i.id == commitId:
                    commit = i
                    break
            if commit is None:
                try: 
                    commit = branch.commits.items[0]
                    logToUser("Failed to find a commit. Receiving Latest", level = 1, plugin = dockwidget)
                except: 
                    logToUser("Failed to find a commit", level = 2, plugin = dockwidget)
                    return None
        return commit
    except Exception as e:
        logToUser(e, level = 2, plugin = dockwidget)
        return

def validateTransport(client: SpeckleClient, streamId: str) -> Union[ServerTransport, None]:
    try: 
        transport = ServerTransport(client=client, stream_id=streamId)
        return transport
    except Exception as e: 
        logToUser("Make sure you have sufficient permissions: " + str(e), level = 1, func = inspect.stack()[0][3])
        return None
