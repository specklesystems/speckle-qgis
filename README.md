<h1 align="center">
  <img src="https://user-images.githubusercontent.com/2679513/131189167-18ea5fe1-c578-47f6-9785-3748178e4312.png" width="150px"/><br/>
  Speckle | QGIS
</h1>

<p align="center"><a href="https://twitter.com/SpeckleSystems"><img src="https://img.shields.io/twitter/follow/SpeckleSystems?style=social" alt="Twitter Follow"></a> <a href="https://speckle.community"><img src="https://img.shields.io/discourse/users?server=https%3A%2F%2Fspeckle.community&amp;style=flat-square&amp;logo=discourse&amp;logoColor=white" alt="Community forum users"></a> <a href="https://speckle.systems"><img src="https://img.shields.io/badge/https://-speckle.systems-royalblue?style=flat-square" alt="website"></a> <a href="https://speckle.guide/dev/"><img src="https://img.shields.io/badge/docs-speckle.guide-orange?style=flat-square&amp;logo=read-the-docs&amp;logoColor=white" alt="docs"></a></p>

> Speckle is the first AEC data hub that connects with your favorite AEC tools. Speckle exists to overcome the challenges of working in a fragmented industry where communication, creative workflows, and the exchange of data are often hindered by siloed software and processes. It is here to make the industry better.

<h3 align="center">
    Connector for Spatial Data from QGIS
</h3>

> [!WARNING]
> This is a legacy QGIS repo! A new next generation connector will be coming soon. In the meantime, check out our active next generation repos here:
> [`speckle-sharp-connectors`](https://github.com/specklesystems/speckle-sharp-connectors): our .NET next generation connectors and desktop UI
> [`speckle-sharp-sdk`](https://github.com/specklesystems/speckle-sharp-sdk): our .NET SDK, Tests, and Objects

## Repo Structure

This repo contains the QGIS plugin for Speckle 2.0. It is written in `python` and uses our fantastic [Python SDK](https://github.com/specklesystems/speckle-py). The [Speckle Server](https://github.com/specklesystems/Server) is providing all the web-facing functionality and can be found [here](https://github.com/specklesystems/Server).

> **Try it out!!**
> Although we're still in early development stages, we encourage you to try out the latest stable release.
> Just follow the instructions on this file, and head to the [Releases page](https://github.com/specklesystems/speckle-qgis/releases) to download the necessary files and dependencies.
>
> **What can it do?**
>
> Currently, the plugin allows to send data from a single layer to a Speckle server using one of the accounts configured on your computer. It will extract all the features of that layer along side their properties and, when possible, geometry too.
> The following geometry types are supported for now:
>
> - Point
> - MultiPoint
> - Polyline (LineString)
> - MultiLineString
> - Polygon
> - MultiPolygon
> - **More to come!!**
>
> Data types currently not supported for sending:
> - Layers depending on the server connection (WMS, WFC, WCS etc.) 
> - Scenes 
> - Mesh Vector layers 
> - Pointclouds 
>
> If you have questions, you can always find us at our [Community forum](https://speckle.community)

## Installation

## QGIS Marketplace

You can find Speckle QGIS in the QGIS `Plugins -> Manage and install plugins` menu item.

The plugin is currently published as experimental, so make sure you go to `Settings` and activate the `Show also experimental plugins` checkbox. 
  
![Experimental](https://github.com/specklesystems/speckle-qgis/assets/89912278/46d638dd-5800-4946-b788-8e0c54ca4c43)


Then go to the `All` tab and search for `Speckle`. You should see the plugin appear in the list. You might need to restart QGIS. 

![image](https://user-images.githubusercontent.com/7717434/129228049-266a1e86-9b1b-48f4-b421-5e1757dd89ad.png)


## Speckle Desktop Manager install

Install Speckle Desktop Manager from [here](https://speckle.systems/download/). Click on QGIS plugin to install it: 
  
![from_manager1](https://github.com/specklesystems/speckle-qgis/assets/89912278/783da098-2754-4b9d-ad0e-0bd2abe14f06)


### Launching the Plugin

SpeckleQGIS will appear in the Plugins Toolbar. Click the blue brick in the toolbar to open the plugin.
  
![plugins_toolbar](https://github.com/specklesystems/speckle-qgis/assets/89912278/6ee68709-0666-4a98-96d8-b7195f431334)

## Developing

### Setup

Setup is a bit cumbersome for now. The following is adapted from [this tutorial](https://www.qgistutorials.com/en/docs/3/building_a_python_plugin.html#get-the-tools)

#### Qt Creator

To edit the UI of the plugin, you'll want to install Qt creator. You can find the free installers on [this page](https://www.qt.io/offline-installers) in the "Qt Creator" tab. On Windows, you'll be prompted to create an account during the installation process.

![qt creator install](https://user-images.githubusercontent.com/7717434/129229210-1899ae09-ec4f-4b52-bf18-99ca75e66292.png)

#### Python Qt Bindings

For Windows, the bindings are already included in the QGIS installation.

For Mac, you can install `PyQt` using [homebrew](https://brew.sh/).

```sh
brew install pyqt
```

#### Install `pb_tool`

`pb_tool` allows you to compile resource files from into something python will understand.

For this plugin we only have one file to convert:

- `resources.qrc` -> `resources.py`

To install `pb_tool`, just run:

```sh
pip install pb_tool

or

YOUR_PYTHON_EXECUTABLE -m pip install pb_tool
```

> For convenience, the pre-compiled `resources.py` file so you don't really have to do anything here.

#### Dev Environment

For a better development experience in your editor, we recommend creating a virtual environment. In the venv, you'll just need to install `specklepy`. You will also need to copy over the `qgis` module into the `{venv}/Lib/site-packages`. You can find the `qgis` module in your QGIS install directory:

- Windows: `C:\Program Files\QGIS 3.28.15\apps\qgis\python`
- MacOS: `/Applications/QGIS.app/Contents/Resources/python`

![qgis dependency for venv](https://user-images.githubusercontent.com/7717434/129324330-1744cc1e-8657-4ef1-90eb-d1ffb2b0229e.png)

### QGIS Plugins

Though it is not required, we recommend installing these plugins from the QGIS Plugin Manager:

- Plugin Reloader (allows you to reload the plugin without restarting QGIS)
- Remote Debugger (enables interactive debugging)
- First Aid (shows errors before crashing QGIS, sometimes)

### Debugging

#### Visual Studio Code

First, you'll need to change the _debug value to True in `plugin_utils/installer.py` file.

```python
    _debug = True
```

This will automatically setup `debugpy` if it's not already installed, and start listening to port `5678`.

Select the "Python" -> "Remote Attach" option. Your `launch.json` should look like this:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "port": 5678,
      "host": "localhost",
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "${workspaceFolder}"
        }
      ]
    }
  ]
}
```

To start debugging, you'll need to first launch QGIS. Once it's running, run your debug `Python: Remote Attach` configuration.

That's all there is to it! Now any breakpoints you create should be hit.

![successful debugging in vs code](https://user-images.githubusercontent.com/7717434/129324011-42ebd156-ba6b-4eca-8b67-22300eb462fc.png)


Enjoy!
