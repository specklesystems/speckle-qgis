
from typing import Union
from specklepy.api.wrapper import StreamWrapper
from specklepy.api.models import Stream, Branch, Commit 
from specklepy.transports.server import ServerTransport
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException, GraphQLException

from speckle.logging import logger
from qgis.core import Qgis
  
def tryGetStream (sw: StreamWrapper) -> Stream:
    client = sw.get_client()
    stream = client.stream.get(sw.stream_id)
    if isinstance(stream, GraphQLException):
        raise SpeckleException(stream.errors[0]['message'])
    return stream

def validateStream(streamWrapper: StreamWrapper) -> Union[Stream, None]:
    try: 
        stream = tryGetStream(streamWrapper)
    except SpeckleException as e:
        logger.logToUser(e.message, Qgis.Warning)
        return None

    if stream.branches is None:
        logger.logToUser("Stream has no branches", Qgis.Warning)
        return None
    return stream

def validateBranch(stream: Stream, branchName: str, checkCommits: bool) ->  Union[Branch, None]:
    branch = None
    for b in stream.branches.items:
        if b.name == branchName:
            branch = b
            break
    if branch is None: 
        logger.logToUser("Failed to find a branch", Qgis.Warning)
        return None
    if checkCommits == True:
        if branch.commits is None:
            logger.logToUser("Failed to find a branch", Qgis.Warning)
            return None
        if len(branch.commits.items)==0:
            logger.logToUser("Branch contains no commits", Qgis.Warning)
            return None
    return branch
            
def validateCommit(branch: Branch, commitId: str) -> Union[Commit, None]:
    commit = None
    try: commitId = commitId.split(" | ")[0]
    except: logger.logToUser("Commit ID is not valid", Qgis.Warning)

    for i in branch.commits.items:
        if i.id == commitId:
            commit = i
            break
    if commit is None:
        try: 
            commit = branch.commits.items[0]
            logger.logToUser("Failed to find a commit. Receiving Latest", Qgis.Warning)
        except: 
            logger.logToUser("Failed to find a commit", Qgis.Warning)
            return None
    return commit

def validateTransport(client: SpeckleClient, streamId: str) -> Union[ServerTransport, None]:
    try: transport = ServerTransport(client=client, stream_id=streamId)
    except: 
        logger.logToUser("Make sure your account has access to the chosen stream", Qgis.Warning)
        return None
    return transport
