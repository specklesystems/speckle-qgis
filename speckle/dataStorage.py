
from typing import List, Tuple, Union


class DataStorage:
    
    project = None
    current_layers: Union[List, None] = None 
    all_layers: Union[List, None] = None 
    savedTransforms: Union[List, None] = None
    transformsCatalog: Union[List, None] = None

    def __init__(self):
        print("hello")
        #self.streamsToFollow = []
        #self.streamsToFollow.append(("https://speckle.xyz/streams/17b0b76d13/branches/random_tests", "", "09a0f3e41a"))
        self.transformsCatalog = ["Extrude polygons by \'height\' attribute (ignore NULL values)",
                                  "Extrude polygons by \'height\' attribute (fill NULL values)",
                                  "Elevation to mesh"]
        self.savedTransforms = []
        all_layers = []
        current_layers = []
        