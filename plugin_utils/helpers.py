import os

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
