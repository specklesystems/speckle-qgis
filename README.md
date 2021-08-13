# Speckle QGIS: The Speckle Connector for QGIS

[![Twitter Follow](https://img.shields.io/twitter/follow/SpeckleSystems?style=social)](https://twitter.com/SpeckleSystems) [![Community forum users](https://img.shields.io/discourse/users?server=https%3A%2F%2Fdiscourse.speckle.works&style=flat-square&logo=discourse&logoColor=white)](https://discourse.speckle.works) [![website](https://img.shields.io/badge/https://-speckle.systems-royalblue?style=flat-square)](https://speckle.systems) [![docs](https://img.shields.io/badge/docs-speckle.guide-orange?style=flat-square&logo=read-the-docs&logoColor=white)](https://speckle.guide/dev/)

<details>
  <summary>What is Speckle?</summary>
  

  Speckle is the Open Source Data Platform for AEC. Speckle allows you to say goodbye to files: we give you object-level control of what you share, infinite versioning history & changelogs. Read more on [our website](https://speckle.systems).

</details>

## Introduction

This repo contains the QGIS plugin for Speckle 2.0. It is written in `python` and uses our fantastic [Python SDK](https://github.com/specklesystems/speckle-py). The [Speckle Server](https://github.com/specklesystems/Server) is providing all the web-facing functionality and can be found [here](https://github.com/specklesystems/Server).

<details>
<summary> Plugin boilerplate generator readme
</summary>

Plugin Builder Results

Your plugin SpeckleQGIS was created in:
    /Users/alan/Documents/Speckle/speckle_qgis

Your QGIS plugin directory is located at:
    /Users/alan/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins

What's Next:

  * Copy the entire directory containing your new plugin to the QGIS plugin
    directory

  * Compile the resources file using pyrcc5

  * Run the tests (``make test``)

  * Test the plugin by enabling it in the QGIS plugin manager

  * Customize it by editing the implementation file: ``speckle_qgis.py``

  * Create your own custom icon, replacing the default icon.png

  * Modify your user interface by opening SpeckleQGIS_dialog_base.ui in Qt Designer

  * You can use the Makefile to compile your Ui and resource files when
    you make changes. This requires GNU make (gmake)

For more information, see the PyQGIS Developer Cookbook at:
http://www.qgis.org/pyqgis-cookbook/index.html

(C) 2011-2018 GeoApt LLC - geoapt.com

</details>

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
- MacOS: 

![site packages](https://user-images.githubusercontent.com/7717434/129223920-d7d428cf-5f56-44e9-a932-7ada175712aa.png)

Drop the *contents* of the included `dependencies` folder (not the folder itself) into the `site-packages` folder to add `specklepy` and all its dependencies to your QGIS environment.

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
- MacOS: 

![qgis dependency for venv](https://user-images.githubusercontent.com/7717434/129324330-1744cc1e-8657-4ef1-90eb-d1ffb2b0229e.png)

### QGIS Plugins

Though it is not required, we recommend installing these plugins from the QGIS Plugin Manager:

- Plugin Reloader (allows you to reload the plugin without restarting QGIS)
- Remote Debugger (enables interactive debugging)

### Debugging

#### Visual Studio Code

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


#### PyCharm

You can set up *remote debugging* in PyCharm Pro. It should work on other IDE's with some configuration.

1. First, create a `Python Debug Server` configuration with the port 53100 and run it.
   ![Screenshot 2021-08-06 at 10 08 25](https://user-images.githubusercontent.com/2316535/128479786-014c0ae9-6710-4f25-8a30-c9155ac881cc.png)

2. Then open QGIS and press the 'Speckle' button to open the pop-up window. Your IDE should hit a breakpoint on `speckle_qgis.py` at first. From then, your app will hit all other breakpoints set in your IDE.

Enjoy!

## Deploy

TBD
