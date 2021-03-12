# 3D Scene Generator
### Tested Blender version:
- 2.81

## Setting up the project
From cmd open Blender python folder and install pip package using this command:
```
Blender_installation_folder\2.81\python\bin\python.exe get-pip.py
```
[get-pip.py](https://pip.pypa.io/en/stable/installing/)

Then go inside Blender python Script folder and install all the package using the requiremets.txt file in the git-repo:
```
Blender_installation_folder\2.81\python\Script\pip.exe install -r requirements.txt
```
To install the add-on:
- download the repository
- unzip all files inside a directory
- then download the pretrained models and unzip inside the repository directory
- finally create a zip with the new created directory
- install the zip as add-on from blender--> Edit\Blender preferences\Add-ons\install\Your_zip.zip
## NOTE!!
Inside the add-on Zip, all files must not be inside an another child folder. 

## Pre-trained Models
   Download -> [link Google Drive](https://drive.google.com/file/d/1yxzH88Ya8jfh9ElombDD1Fkjpy7NEn30/view?usp=sharing)

## Abstract

The aim of this project is to generate a 3D scene basing on a single input image.

Languges: 
Python

Main technologies and libraries: 
Blender API (bpy), [XiaohuLuVPDetection](https://github.com/rayryeng/XiaohuLuVPDetection), [Camera Calibration PVR](https://github.com/mrossini-ethz/camera-calibration-pvr), [Image AI](https://github.com/OlafenwaMoses/ImageAI), [FCRN-DepthPrediction](https://github.com/iro-cp/FCRN-DepthPrediction)

## Project structure

![Structure](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/project_structure.JPG "Project structure")

## Camera Calibration

This step consists in calibrating the camera in order to match as much as possible the external and internal original parameters.

To do so, Marco Rossini’s library takes as input a rectangle with two dangling vertices. The edges of the mesh must follow the perspective lines for the calibration to work properly.

### VPs normalization

XiaohuLu’s library enabled us to generate this input using the vanishing points. 
However, the library returns the vanishing points, expressed in pixel units, in a reference system that has the bottom-left corner of the image as origin.
Instead, when the reference image is imported in Blender, its dimensions are expressed in metres and the origin of the 3D World match the center of the image.
So, we compute the new coordinates of the vanishing points in the reference system with the origin in the center of the image. 

![system_change](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/system_change.png "Reference system change")

```
vp1[0] = vp1[0] - img_x/2
vp1[1] = vp1[1] - img_y/2

vp2[0] = vp2[0] - img_x/2
vp2[1] = vp2[1] - img_y/2

vp3[0] = vp3[0] - img_x/2
vp3[1] = vp3[1] - img_y/2
```

Now, we need to express the coordinates in metres (the unity used in Blender). Since Blender matches the longer dimension of the imported image with 5 metres, the scaling factor can be computed:

![Blender importing](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/image_proportions.png "Blender importing")

```
if (img_x>img_y):
            scaling_factor = img_x/5
else:
            scaling_factor = img_y/5
```

### Rectangle mesh creation

The rectangle with two dangling vertices is then generated using a function implemented in Marco Rossini’s library (intersect_2d), that solves linear systems in order to compute the coordinates of the intersection between two lines.

![Rectangle creation](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/rectangle_creation.png "Rectangle creation")

### Object rotation

After the calibration, we also snap the camera to the origin of the 3D World and rotate it in order to match the x and y axis with the perspective lines of the first two vanishing points, and the z axis with the third. 
In this way, when an object is inserted in the scene, its rotation is orthogonal to the camera direction. Especially in internal scenes, most of the objects present this rotation.

![Object rotation](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/rotation.png "Object rotation")

The calibration tool is started.

## Positioning

WIP

## Mesh Database

### Library

The detected objects are imported as meshes from a .blend library (3d_scene_generator/Mesh Database/entire_collection.blend) containing the models of the most frequent labels.
Thanks to the format (.blend), the imported objects embed shaders (materials and textures) and the physics properties.

### Shading

We chose a cell shading with outlines (evee freestyle activated) in order to represent the scene in the clearest way possible.

![Shader](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/render.png "Shader")

To do so, we used the Diffuse shader and ‘discretize’ the rgb values into two flat shades (black or white) thanks to a threshold defined in the Color Ramp node.The output is then mixed with a base color (‘multiply’ blending mode). 
Therefore, a specular reflection is added (‘add’ blending mode) using a Glossy shader (also discretized with a Color Ramp node).
The final output is then mixed (‘multiply’ blending mode) with a texure (we used images or procedural patterns in some cases).

![Shader Nodes](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/shader.png "Shader Nodes")

## Room Generation and Physics

This step is ideally suited for internal scenes. 
It consists in generating a floor and two walls, and activate gravity in order to place the objects on the surface below (the floor or other objects).
In order to do so, we suppose the size of the room basing on the objects that are present in the scene.

### Floor

In particular, we compute the lowest vertex (z-axis) for every object in the room and consider the minimum among these, then import the floor object and set its position to the minimum.

```
# this code is simplified with respect to the real one

for obj in bpy.data. obects:
	min_z = obj.computeLower_z()
	if ( min_z < ground_position ):
		ground_position = min_z
```

![Floor](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/floor.png "Floor")

### Walls

We further repeat this idea to generate the walls on x and y axis.

![Room generation](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/render_nogravity.png "Room generation")

### Physics

At this point, for each object, we lock all the possible transformations but the translation on the z-axis, and force the computation of the frame 50 (supposing that in this frame all the objects fell on the surfaces below).

![Physics](https://github.com/logicesecutor/3D_scene_generator/blob/main/doc/render_gravity.png "Physics") 



