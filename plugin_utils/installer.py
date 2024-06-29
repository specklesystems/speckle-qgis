"""
Provides uniform and consistent path helpers for `specklepy`
"""

import os
import sys
from pathlib import Path
from typing import Optional
from importlib import import_module, invalidate_caches
import pkg_resources
from subprocess import run
import shutil

from speckle.utils.utils import get_qgis_python_path

_user_data_env_var = "SPECKLE_USERDATA_PATH"
_debug = False
_vs_code_directory = os.path.expanduser(
    "~\.vscode\extensions\ms-python.python-2023.20.0\pythonFiles\lib\python"
)


def _path() -> Optional[Path]:
    """Read the user data path override setting."""
    path_override = os.environ.get(_user_data_env_var)
    if path_override:
        return Path(path_override)
    return None


_application_name = "Speckle"


def override_application_name(application_name: str) -> None:
    """Override the global Speckle application name."""
    global _application_name
    _application_name = application_name


def override_application_data_path(path: Optional[str]) -> None:
    """
    Override the global Speckle application data path.

    If the value of path is `None` the environment variable gets deleted.
    """
    if path:
        os.environ[_user_data_env_var] = path
    else:
        os.environ.pop(_user_data_env_var, None)


def _ensure_folder_exists(base_path: Path, folder_name: str) -> Path:
    path = base_path.joinpath(folder_name)
    path.mkdir(exist_ok=True, parents=True)
    return path


def user_application_data_path() -> Path:
    """Get the platform specific user configuration folder path"""
    path_override = _path()
    if path_override:
        return path_override

    try:
        if sys.platform.startswith("win"):
            app_data_path = os.getenv("APPDATA")
            if not app_data_path:
                raise Exception("Cannot get appdata path from environment.")
            return Path(app_data_path)
        else:
            # try getting the standard XDG_DATA_HOME value
            # as that is used as an override
            app_data_path = os.getenv("XDG_DATA_HOME")
            if app_data_path:
                return Path(app_data_path)
            else:
                return _ensure_folder_exists(Path.home(), ".config")
    except Exception as ex:
        raise Exception("Failed to initialize user application data path.", ex)


def user_speckle_folder_path() -> Path:
    """Get the folder where the user's Speckle data should be stored."""
    return _ensure_folder_exists(user_application_data_path(), _application_name)


def user_speckle_connector_installation_path(host_application: str) -> Path:
    """
    Gets a connector specific installation folder.

    In this folder we can put our connector installation and all python packages.
    """
    return _ensure_folder_exists(
        _ensure_folder_exists(user_speckle_folder_path(), "connector_installations"),
        host_application,
    )


print("Starting module dependency installation")
print(sys.executable)

PYTHON_PATH = get_qgis_python_path()


def connector_installation_path(host_application: str) -> Path:
    connector_installation_path = user_speckle_connector_installation_path(
        host_application
    )
    connector_installation_path.mkdir(exist_ok=True, parents=True)

    # set user modules path at beginning of paths for earlier hit
    if sys.path[0] != connector_installation_path:
        sys.path.insert(0, str(connector_installation_path))

    print(f"Using connector installation path {connector_installation_path}")
    return connector_installation_path


def is_pip_available() -> bool:
    try:
        import_module("pip")  # noqa F401
        return True
    except ImportError:
        return False


def ensure_pip() -> None:
    print("Installing pip... ")

    print(PYTHON_PATH)

    completed_process = run([PYTHON_PATH, "-m", "ensurepip"])

    if completed_process.returncode == 0:
        print("Successfully installed pip")
    else:
        raise Exception(
            f"Failed to install pip, got {completed_process.returncode} return code"
        )


def get_requirements_path() -> Path:
    # we assume that a requirements.txt exists next to the __init__.py file
    if sys.platform.lower().startswith("darwin"):
        path = Path(Path(__file__).parent, "requirements_mac.txt")
    path = Path(Path(__file__).parent, "requirements.txt")
    assert path.exists(), f"path not found {path}"
    return path


def _dependencies_installed(requirements: str, path: str) -> bool:
    for d in pkg_resources.find_distributions(path):
        entry = f"{d.key}=={d.version}"
        if entry in requirements:
            requirements = requirements.replace(entry, "")
    requirements = requirements.replace(" ", "").replace(";", "").replace(",", "")
    if len(requirements) > 0:
        return False
    print("Dependencies already installed")
    return True


def install_requirements(host_application: str) -> None:
    # set up addons/modules under the user
    # script path. Here we'll install the
    # dependencies
    requirements = get_requirements_path().read_text().replace("\n", "")
    path = str(connector_installation_path(host_application))

    print(f"Installing debugpy to {path}")

    if _dependencies_installed(requirements, path):
        return

    try:
        shutil.rmtree(path)
    except PermissionError as e:
        raise Exception("Restart QGIS for changes to take effect")

    print(f"Installing Speckle dependencies to {path}")
    from subprocess import run

    completed_process = run(
        [
            PYTHON_PATH,
            "-m",
            "pip",
            "install",
            "-t",
            str(path),
            "-r",
            str(get_requirements_path()),
        ],
        capture_output=True,
    )

    if completed_process.returncode != 0:
        m = f"Failed to install dependenices through pip, got {completed_process.returncode} as return code. Full log: {completed_process}"
        print(m)
        print(completed_process.stdout)
        print(completed_process.stderr)
        raise Exception(m)


def install_dependencies(host_application: str) -> None:
    if not is_pip_available():
        ensure_pip()

    install_requirements(host_application)


def _import_dependencies() -> None:
    import_module("specklepy")
    # the code above doesn't work for now, it fails on importing graphql-core
    # despite that, the connector seams to be working as expected
    # But it would be nice to make this solution work
    # it would ensure that all dependencies are fully loaded
    # requirements = get_requirements_path().read_text()
    # reqs = [
    #     req.split(" ; ")[0].split("==")[0].split("[")[0].replace("-", "_")
    #     for req in requirements.split("\n")
    #     if req and not req.startswith(" ")
    # ]
    # for req in reqs:
    #     print(req)
    #     import_module("specklepy")


def ensure_dependencies(host_application: str) -> None:
    try:
        install_dependencies(host_application)
        invalidate_caches()
        # _import_dependencies()
        print("Successfully found dependencies")
    except ImportError:
        raise Exception(
            f"Cannot automatically ensure Speckle dependencies. Please try restarting the host application {host_application}!"
        )


def startDebugger() -> None:
    if _debug is True:
        try:
            import debugpy
        except:
            # path = str(connector_installation_path(host_application))
            completed_process = run(
                [
                    PYTHON_PATH,
                    "-m",
                    "pip",
                    "install",
                    "debugpy==1.8.0",
                ],
                capture_output=True,
            )
            if completed_process.returncode != 0:
                m = f"Failed to install debugpy through pip. Disable debug mode or install debugpy manually. Full log: {completed_process}"
                raise Exception(completed_process)

    # debugger: https://gist.github.com/giohappy/8a30f14678aa7e446f9b694c632d7089
    if _debug is True:
        import debugpy

        sys.path.append(_vs_code_directory)
        debugpy.configure(python=PYTHON_PATH)  # shutil.which("python"))

        debugpy.listen(("localhost", 5678))
        debugpy.wait_for_client()


# path = str(connector_installation_path("QGIS"))
# print(path)
