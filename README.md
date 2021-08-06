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

## Setup

Setup is a bit cumbersome for now. First, follow the instructions on the "Get the tools" section of [this tutorial](https://www.qgistutorials.com/en/docs/3/building_a_python_plugin.html#get-the-tools)

You'll also need to manually install `specklepy` on your QGIS python interpeter.

- Find your interpeter's path:
  - Windows: `C:\Program Files\QGIS 3.20.1\apps\Python39\Lib\`
  - Mac: `/Applications/QGIS.app/Contents/MacOS/bin`
- Use the command line to install `specklepy`
  - `QGIS_PYTHON_PATH -m pip install specklepy`


**THIS WILL NOT WORK ON DEPLOYMENT, WE NEED TO COME UP WITH A BETTER STRATEGY BUT FOR DEV PURPOSES ITS FINE FOR NOW**

### QGIS Plugins

It is not required, but extremelly recommended, to install these plugins from the QGIS Plugin Manager:

- Plugin Reloader
- Remote Debugger

## Debug

Only *remote debugging* has been successfully set up in PyCharm. It should work on other IDE's with some configuration.

1. First, create a `Python Debug Server` configuration with the port 53100 and run it.
2. Then open QGIS and press the 'Speckle' button to open the pop-up window. Your IDE should hit a breakpoint on `speckle_qgis.py` at first. From then, your app will hit all other breakpoints set in your IDE.

Enjoy!

## Deploy

TBD