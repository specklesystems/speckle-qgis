import os
from typing import List
from textwrap import wrap

SYMBOL = "_x_x_"

def jsonFromList(jsonObj: dict, levels: list):
    #print("jsonFromList")
    if len(levels) == 0: return jsonObj
    lastLevel = jsonObj
    for l in levels:
        #print(lastLevel)
        try: 
            lastLevel = lastLevel[l]
        except: 
            lastLevel.update({l: {}})
    #print(jsonObj)
    return jsonObj 

def constructCommitURL(streamWrapper, branch_id: str = None, commit_id: str = None) -> str:
    import requests 
    streamUrl = streamWrapper.stream_url.split("?")[0].split("&")[0].split("@")[0]
    r = requests.get(streamUrl)
    
    url = streamUrl 
    # check for frontend2 
    try: 
        header = r.headers['x-speckle-frontend-2']
        url = streamUrl.replace("streams", "projects") + "/models/" + branch_id + "@" + commit_id
    except:
        url = streamUrl.replace("projects", "streams") + "/commits/" + commit_id
    return url 

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
    new_text = text.replace("<","_").replace(">","_").replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("|","_").replace("\"","_").replace("\'","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_").replace(",","_").replace(".","_")
    new_text = new_text.replace("_____","_").replace("____","_").replace("___","_").replace("__","_")
    return new_text

def splitTextIntoLines(text: str = "", number: int= 40) -> str: 
    #print("__splitTextIntoLines")
    #print(text)
    msg = ""
    try:
        if len(text)>number:
            try:
                lines = wrap(text, number)
                for i, x in enumerate(lines):
                    msg += x
                    if i!= len(lines) - 1: 
                        msg += "\n"
            except Exception as e: print(e)
        else: 
            msg = text
    except Exception as e:
        print(e)
        #print(text)
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
                except: 
                    try: # if all vertices colors are the same, apply it 
                        sameColors = True
                        color1 = f.colors[0]
                        for c in f.colors:
                            if c != color1: 
                                sameColors = False
                                break 
                        if sameColors is True: 
                            fetColors.append(f.colors[0]) 
                            colorFound += 1
                    except: pass
    if colorFound == 0: 
        fetColors.append(None)
    return fetColors 