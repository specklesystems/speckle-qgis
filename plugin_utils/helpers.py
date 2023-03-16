import os

def findOrCreatePath(path: str):
    if not os.path.exists(path): 
        os.makedirs(path)

def removeSpecialCharacters(text: str) -> str:
    
    new_text = text.encode('iso-8859-1', errors='ignore').decode('utf-8')
    return new_text