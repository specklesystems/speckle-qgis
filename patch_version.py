import re
import sys

def patch_installer(tag):
    """Patches the installer with the correct connector version and specklepy version"""
    iss_file = "speckle-sharp-ci-tools/qgis.iss"
    metadata = "metadata.txt"
    #conda_file = "speckle_arcgis_installer/conda_clone_activate.py"
    #toolbox_install_file = "speckle_arcgis_installer/toolbox_install.py"
    #toolbox_manual_install_file = "speckle_arcgis_installer/toolbox_install_manual.py"

    #py_tag = get_specklepy_version()
    try:
        with open(iss_file, "r") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if "#define AppVersion " in line: 
                    lines[i] = f'#define AppVersion "{tag.split("-")[0]}"\n'
                if "#define AppInfoVersion " in line: 
                    lines[i] = f'#define AppInfoVersion "{tag}"\n'
            with open(iss_file, "w") as file:
                file.writelines(lines)
                print(f"Patched installer with connector v{tag} ")
        file.close()
    except: pass
    

    with open(metadata, "r") as file:
        lines = file.readlines()
        for i, line in enumerate(lines):
            if "version=" in line: 
                lines[i] = f'version={tag}\n'#.split("-")[0]
                break
        with open(metadata, "w") as file:
            file.writelines(lines)
            print(f"Patched metadata v{tag} ")
    file.close()

    r'''
    def whlFileRename(fileName: str): 
        with open(fileName, "r") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if "-py3-none-any.whl" in line: 
                    p1 = line.split("-py3-none-any.whl")[0].split("-")[0]
                    p2 = f'{tag.split("-")[0]}'
                    p3 = line.split("-py3-none-any.whl")[1]
                    lines[i] = p1+"-"+p2+"-py3-none-any.whl"+p3
            with open(fileName, "w") as file:
                file.writelines(lines)
                print(f"Patched toolbox_installer with connector v{tag} and specklepy ")
        file.close()

    whlFileRename(conda_file)
    whlFileRename(toolbox_install_file)
    whlFileRename(toolbox_manual_install_file)
    '''


def main():
    if len(sys.argv) < 2:
        return

    tag = sys.argv[1]
    if not re.match(r"([0-9]+)\.([0-9]+)\.([0-9]+)", tag):
        raise ValueError(f"Invalid tag provided: {tag}")

    print(f"Patching version: {tag}")
    #patch_connector(tag.split("-")[0]) if I need to edit a connector file
    patch_installer(tag)


if __name__ == "__main__":
    main()