import os
from typing import List

def getFirstMatchingLayerByName(project, name: str):
    from qgis.core import QgsLayerTreeLayer
    
    root = project.layerTreeRoot()
    new_layer = None
    for child in root.children():
        if isinstance(child, QgsLayerTreeLayer): 
            if child.name() == name:
                new_layer = child.layer()
                try: new_layer = new_layer.layer()
                except: pass
                return new_layer

def getAppName(name: str) -> str:
    new_name = ""
    for i, x in enumerate(str(name)):
        if x.lower() in [a for k,a in enumerate("abcdefghijklmnopqrstuvwxyz")]:
            new_name += x
        else: break
    return new_name

def findOrCreatePath(path: str):
    if not os.path.exists(path): 
        os.makedirs(path)

def removeSpecialCharacters(text: str) -> str:
    new_text = text.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")
    #new_text = text.encode('iso-8859-1', errors='ignore').decode('utf-8')
    return new_text

def splitTextIntoLines(text: str = "", number: int= 40) -> str: 
    print("__splitTextIntoLines")
    print(text)
    msg = ""
    try:
        if len(text)>number:
            try:
                for i, x in enumerate(text):
                    msg += x
                    if i!=0 and i%number == 0: msg += "\n"
            except Exception as e: print(e)
        else: 
            msg = text
    except Exception as e:
        print(e)
        print(text)
    
    return msg

def findFeatColors(fetColors: List, f):
    colorFound = 0
    try: # get render material from any part of the mesh (list of items in displayValue)
        for k, item in enumerate(f.displayValue):
            try:
                fetColors.append(item.renderMaterial.diffuse)  
                colorFound += 1
                break
            except: pass
        if colorFound == 0: fetColors.append(f.renderMaterial.diffuse)
    except: # if no "DisplayValue"
        try:
            for k, item in enumerate(f["@displayValue"]):
                try: 
                    fetColors.append(item.renderMaterial.diffuse) 
                    colorFound += 1
                    break
                except: pass
            if colorFound == 0: fetColors.append(f.renderMaterial.diffuse)
        except: 
            # the Mesh itself has a renderer 
            try: # get render material from any part of the mesh (list of items in displayValue)
                fetColors.append(f.renderMaterial.diffuse)  
                colorFound += 1
            except: 
            
                try:
                    fetColors.append(f.displayStyle.color) 
                    colorFound += 1
                except: pass
    if colorFound == 0: 
        fetColors.append(None)
    return fetColors 