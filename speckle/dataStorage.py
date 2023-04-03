


from typing import List, Tuple, Union


class DataStorage:
    streamsToFollow: Union[List[Tuple[str, str, str]], None] = None #url, uuid, commitID
    project = None
    runUpdates: bool = True

    def __init__(self):
        print("hello")
        self.streamsToFollow = []
        self.streamsToFollow.append(("https://speckle.xyz/streams/17b0b76d13/branches/random_tests", "", "09a0f3e41a"))
