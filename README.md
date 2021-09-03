<h1 align="center">
  <img src="https://user-images.githubusercontent.com/2679513/131189167-18ea5fe1-c578-47f6-9785-3748178e4312.png" width="150px"/><br/>
  Speckle | QGIS
</h1>
<h3 align="center">
    Connector for Spatial Data from QGIS
</h3>
<p align="center"><b>Speckle</b> is data infrastructure for the AEC industry.</p><br/>

<p align="center"><a href="https://twitter.com/SpeckleSystems"><img src="https://img.shields.io/twitter/follow/SpeckleSystems?style=social" alt="Twitter Follow"></a> <a href="https://speckle.community"><img src="https://img.shields.io/discourse/users?server=https%3A%2F%2Fspeckle.community&amp;style=flat-square&amp;logo=discourse&amp;logoColor=white" alt="Community forum users"></a> <a href="https://speckle.systems"><img src="https://img.shields.io/badge/https://-speckle.systems-royalblue?style=flat-square" alt="website"></a> <a href="https://speckle.guide/dev/"><img src="https://img.shields.io/badge/docs-speckle.guide-orange?style=flat-square&amp;logo=read-the-docs&amp;logoColor=white" alt="docs"></a></p>
<p align="center">

# About Speckle

What is Speckle? Check our ![YouTube Video Views](https://img.shields.io/youtube/views/B9humiSpHzM?label=Speckle%20in%201%20minute%20video&style=social)

### Features

- **Object-based:** say goodbye to files! Speckle is the first object based platform for the AEC industry
- **Version control:** Speckle is the Git & Hub for geometry and BIM data
- **Collaboration:** share your designs collaborate with others
- **3D Viewer:** see your CAD and BIM models online, share and embed them anywhere
- **Interoperability:** get your CAD and BIM models into other software without exporting or importing
- **Real time:** get real time updates and notifications and changes
- **GraphQL API:** get what you need anywhere you want it
- **Webhooks:** the base for a automation and next-gen pipelines
- **Built for developers:** we are building Speckle with developers in mind and got tools for every stack
- **Built for the AEC industry:** Speckle connectors are plugins for the most common software used in the industry such as Revit, Rhino, Grasshopper, AutoCAD, Civil 3D, Excel, Unreal Engine, Unity, QGIS (you are here), Blender and more!

### Try Speckle now!

Give Speckle a try in no time by:

- [![speckle XYZ](https://img.shields.io/badge/https://-speckle.xyz-0069ff?style=flat-square&logo=hackthebox&logoColor=white)](https://speckle.xyz) ⇒ creating an account at 
- [![create a droplet](https://img.shields.io/badge/Create%20a%20Droplet-0069ff?style=flat-square&logo=digitalocean&logoColor=white)](https://marketplace.digitalocean.com/apps/speckle-server?refcode=947a2b5d7dc1) ⇒ deploying an instance in 1 click 

### Resources

- [![Community forum users](https://img.shields.io/badge/community-forum-green?style=for-the-badge&logo=discourse&logoColor=white)](https://speckle.community) for help, feature requests or just to hang with other speckle enthusiasts, check out our community forum!
- [![website](https://img.shields.io/badge/tutorials-speckle.systems-royalblue?style=for-the-badge&logo=youtube)](https://speckle.systems) our tutorials portal is full of resources to get you started using Speckle
- [![docs](https://img.shields.io/badge/docs-speckle.guide-orange?style=for-the-badge&logo=read-the-docs&logoColor=white)](https://speckle.guide/dev/) reference on almost any end-user and developer functionality

![Untitled](https://user-images.githubusercontent.com/2679513/132021739-15140299-624d-4410-98dc-b6ae6d9027ab.png)

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
> - Multipoint
> - Polyline (LineString)
> - MultiLineString
> - Polygon
> - MultiPolygon
> - **More to come!!**
>
> If you have questions, you can always find us at our [Community forum](https://speckle.community)

## Installation

This plugin is still in early development and should only be used for testing. If you'd like to be an early tester and provide us with feedback and feature requests, forge ahead!

### Adding the Plugin

First, you'll need to place the `speckle_qgis` folder into your plugins folder. To find this folder, go to the "Settings" menu and select "User Profiles" > "Open Active Profile Folder".

![active project folder](https://user-images.githubusercontent.com/7717434/129204454-11685461-cfe2-483a-8f91-77b5e8e8107b.png)

Inside this folder, navigate into the `python` folder then the `plugins` folder. Once inside the `plugins` folder, drop your `speckle_qgis` folder into it.

![plugins folder](https://user-images.githubusercontent.com/7717434/129224685-896b6102-746c-4c86-84eb-55226161f9ac.png)

### Speckle Dependencies

Before you can launch the plugin, you'll need to add the Speckle dependencies. To do this, you'll need to head to your QGIS installation folder and find the Python `site-packages` folder. This is in a different location from your plugins folder.

For QGIS 3.20, you'll find this folder at:

- Windows: `C:\Program Files\QGIS 3.20.1\apps\Python39\Lib\site-packages`
- MacOS: `/Applications/QGIS.app/Contents/Resources/python/site-packages`

![site packages](https://user-images.githubusercontent.com/7717434/129223920-d7d428cf-5f56-44e9-a932-7ada175712aa.png)

Drop the _contents_ of the included `dependencies` folder (not the folder itself) into the `site-packages` folder to add `specklepy` and all its dependencies to your QGIS environment.

![specklepy in packages folder](https://user-images.githubusercontent.com/7717434/129224484-24afc749-4d41-4dbc-9d02-dff5ee5a7358.png)

### Launching the Plugin

You should now launch QGIS and you should see SpeckleQGIS in your installed plugins. Click the blue brick in the toolbar to open the plugin.

![image](https://user-images.githubusercontent.com/7717434/129228049-266a1e86-9b1b-48f4-b421-5e1757dd89ad.png)

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

#### Installing `specklepy`

You'll also need to manually install `specklepy` in the QGIS python environment. This will add `specklepy` and its dependencies to the QGIS python's `site-packages` folder.

- Find your interpreter's path:
  - Windows: `C:\Program Files\QGIS 3.20.1\apps\Python39\`
  - Mac: `/Applications/QGIS.app/Contents/MacOS/bin`
- Use the command line to install `specklepy`
  - `QGIS_PYTHON_PATH -m pip install specklepy`

**THIS WILL NOT WORK ON DEPLOYMENT, WE NEED TO COME UP WITH A BETTER STRATEGY BUT FOR DEV PURPOSES ITS FINE FOR NOW**

#### Dev Environment

For a better development experience in your editor, we recommend creating a virtual environment. In the venv, you'll just need to install `specklepy`. You will also need to copy over the `qgis` module into the `{venv}/Lib/site-packages`. You can find the `qgis` module in your QGIS install directory:

- Windows: `C:\Program Files\QGIS 3.20.1\apps\qgis\python`
- MacOS: `/Applications/QGIS.app/Contents/Resources/python`

![qgis dependency for venv](https://user-images.githubusercontent.com/7717434/129324330-1744cc1e-8657-4ef1-90eb-d1ffb2b0229e.png)

### QGIS Plugins

Though it is not required, we recommend installing these plugins from the QGIS Plugin Manager:

- Plugin Reloader (allows you to reload the plugin without restarting QGIS)
- Remote Debugger (enables interactive debugging)
- First Aid (shows errors before crashing QGIS, sometimes)

### Debugging

#### Visual Studio Code

##### If running on Windows

In VS Code, you can use the built in python debugger. You'll need to create a debug configuration by creating a `launch.json` file.

![create debug config](https://user-images.githubusercontent.com/7717434/129330416-87513b88-4138-4fc8-ae73-5c2d2846ebd8.png)

Select the "Python" -> "Attach using Process ID" option. Your `launch.json` should look like this:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Attach using Process Id",
      "type": "python",
      "request": "attach",
      "processId": "${command:pickProcess}"
    }
  ]
}
```

To start debugging, you'll need to first launch QGIS. Once it's running, run your debug configuration. You'll see a dropdown where you can search for and select the `qgis-bin.exe` process.

![select process to attach to](https://user-images.githubusercontent.com/7717434/129324015-7a294488-235c-4004-bc6d-c147a4e597e6.png)

That's all there is to it! Now any breakpoints you create should be hit.

![successful debugging in vs code](https://user-images.githubusercontent.com/7717434/129324011-42ebd156-ba6b-4eca-8b67-22300eb462fc.png)

##### If running on Mac

> The previous instructions don't work on a Mac (at least the ones we tested), as QGIS seems to freeze when attaching to it's process. If you managed to make it work, or we're missing something, do let us know!

First, you'll need to install `ptvsd` the same way you installed `specklepy` above, so that QGIS will be able to find and use it.

```
QGIS_PYTHON_PATH -m pip install ptvsd
```

In VS Code, you can use the built in python debugger. You'll need to create a debug configuration by creating a `launch.json` file.

![Create Debug Config](https://user-images.githubusercontent.com/2316535/129895259-3b9ede24-a898-4dbd-86df-0d15f19a2714.png)

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

## Deploy

TBD
