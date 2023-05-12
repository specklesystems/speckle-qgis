## Features

### Transformations
From 2.14 version onwards there is a new functionality helping to send a full 3d context maps for the further use in CAD, BIM or any 3D software. This can be applied by clicking "Apply transformations on Send" before sending the data. 
![transforms_intro](https://github.com/specklesystems/speckle-qgis/assets/89912278/450b4c21-bb6e-4526-8d7b-2e8d3a96eb92)

At the moment, 4 types of transformations are available: 

- **Creating a mesh from Digital Elevation Model:** converting a sigle-band raster layer to a 3d mesh. 
- **Using a raster layer as a texture for a 3d mesh:** mapping the raster image onto a 3d elevation (requires pre-selected Elevation layer). 
- **Extruding polygons:** using a random value or a numeric/text attribute field of the layer. 
- **Projecting polygons onto 3d elevation:** move the lowest point of the polygon to the lowest point of the surrounding terrain (requires pre-selected Elevation layer). 
![transforms_types](https://github.com/specklesystems/speckle-qgis/assets/89912278/83761c76-67b7-4321-9d18-bdda6eb2e1b7)

Additionally: 
- **Setting a layer as Elevation layer:** will be used as a base for several transformations, such as texturing and projecting on a terrain. 
![transforms_elevation_layer](https://github.com/specklesystems/speckle-qgis/assets/89912278/dced2224-3f7a-4736-89cf-d824d81ebfd8)

You can add and remove transformations using + and - buttons above and under the list with applied transformations: 
![transforms_add](https://github.com/specklesystems/speckle-qgis/assets/89912278/8f6e9894-15c6-4ea8-bf16-5da0df276076)


Each transformations type is targeting a specific layer type, e.g. only polygon layers or only raster layers. Extrusion transformation will offer additional parameter - choice of the attribute to use for the extrusion value. If you choose the option "populate NULL values", you will be able to set a "Random height" as a value. 
![transforms_extrusion_attributes](https://github.com/specklesystems/speckle-qgis/assets/89912278/5caa713f-c361-4c84-8e59-2b9c15d948a5)

Add "Log Messages Panel" to your QGIS interface to see more info and warnings about your transformations. 

### Examples

**Elevation to a 3d mesh**
![2 14-changelog-01-elevation](https://github.com/specklesystems/speckle-qgis/assets/89912278/3aba9b66-d8b5-4d13-8070-74714b2a04a5)

**Texture for 3d mesh**
![2 14-changelog-02-texture](https://github.com/specklesystems/speckle-qgis/blob/main/speckle/automation/img/2.14-changelog-02-texture_over_elevation.gif)

**Polygon extrusions**
![2 14-changelog-03-extrusion](https://github.com/specklesystems/speckle-qgis/assets/89912278/65c50302-0a98-4f32-9f84-37da5108a258)

**Extrusing and projecting on a terrain**
![2 14-changelog-04-projecting](https://github.com/specklesystems/speckle-qgis/blob/main/speckle/automation/img/2.14-changelog-04-extrude_and_project_smaller_smaller.gif)

**Combination of the transformations**
![2 14-changelog-05-all-transforms](https://github.com/specklesystems/speckle-qgis/blob/main/speckle/automation/img/2.14-changelog-05-altogether_smaller.gif)


If you have questions, you can always find us at our [Community forum](https://speckle.community)! 
