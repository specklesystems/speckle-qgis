import copy
from typing import Dict


def findUpdateJsonItemPath(tree: Dict, full_path_str: str):
    new_tree = copy.deepcopy(tree)

    path_list = full_path_str.split("_x_x_")
    attr_found = False

    for i, item in enumerate(new_tree.items()):
        attr, val_dict = item
        print("______________")
        print(i)
        print(item)

        if attr == path_list[0]: 
            attr_found = True 
            path_list.pop(0)
            if len(path_list)>0: # if the path is not finished: 
                all_names = val_dict.keys() 
                if len(path_list) == 1 and path_list[0] in all_names: # already in a tree
                    return new_tree
                else:
                    branch = findUpdateJsonItemPath(val_dict, "_x_x_".join(path_list)) 
                    print("BRANCH")
                    print(branch)
                    new_tree.update({attr:branch}) 
    
    if attr_found is False and len(path_list)>0: # create a new branch at the top level 
        print("Not found: " + str(path_list[0]))
        if len(path_list) == 1:
            new_tree.update({path_list[0]:{}})
            return new_tree
        else:
            branch = findUpdateJsonItemPath({path_list[0]:{}}, "_x_x_".join(path_list)) 
            print("BRANCH CREATE")
            print(branch)
            new_tree.update(branch) 

    return new_tree 
                
    
treeStart = {"01":{"02":{"03":{}}}}
print(findUpdateJsonItemPath(treeStart, "01 >>|<< 03 >>|<< 04 >>|<< 05"))
