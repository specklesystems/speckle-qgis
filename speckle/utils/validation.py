
import inspect
from typing import Union
from specklepy.core.api.wrapper import StreamWrapper
from specklepy.core.api.models import Stream, Branch, Commit 
from specklepy.transports.server import ServerTransport
from specklepy.core.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException, GraphQLException

from speckle.utils.panel_logging import logToUser

def tryGetClient(sw: StreamWrapper, dataStorage, write = False, dockwidget = None):
    # only streams with write access 
    try:
        client = None
        savedRole = None
        savedStreamId = None
        for acc in dataStorage.accounts:
            # only check accounts on selected server 
            if acc.serverInfo.url in sw.server_url:
                client = SpeckleClient( acc.serverInfo.url, acc.serverInfo.url.startswith("https") )
                client.authenticate_with_account(acc)
                if client.account.token is not None:
                    stream = client.stream.get(id = sw.stream_id, branch_limit = 100, commit_limit = 100)
                    if isinstance(stream, Stream): 
                        #print(stream.role)
                        if write == False:
                            # try get stream, only read access needed
                            #print("only read access needed")
                            return client, stream 
                        else: 
                            # check write access 
                            #print("write access needed")
                            if stream.role is None or (isinstance(stream.role, str) and "reviewer" in stream.role):
                                savedRole = stream.role 
                                savedStreamId = stream.id
                            else: 
                                return client, stream 
        if savedRole is not None and savedStreamId is not None:
            logToUser(f"You don't have write access to the stream '{savedStreamId}'. You role is '{savedRole}'", level = 2, func = inspect.stack()[0][3], plugin = dockwidget)

        return None, None
    except Exception as e: 
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = dockwidget)
        return None, None

def tryGetStream(sw: StreamWrapper, dataStorage, write = False, dockwidget = None) -> Stream:
    try:
        #print("tryGetStream")
        client, stream = tryGetClient(sw, dataStorage, write, dockwidget)
        return stream
    except Exception as e:
        logToUser(e, level = 2, func = inspect.stack()[0][3], plugin = dockwidget)
        return None 

def validateStream(stream: Stream, dockwidget) -> Union[Stream, None]:
    try: 
        #dockwidget.dataStorage.check_for_accounts()
        #stream = tryGetStream(streamWrapper, dockwidget.dataStorage)

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
        #print(transport)
        return transport
    except Exception as e: 
        logToUser("Make sure you have sufficient permissions: " + str(e), level = 1, func = inspect.stack()[0][3])
        return None
