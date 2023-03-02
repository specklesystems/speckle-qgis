import os

def findOrCreatePath(path: str):
    if not os.path.exists(path): 
        os.makedirs(path)
