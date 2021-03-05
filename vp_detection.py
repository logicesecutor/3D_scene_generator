import bpy

class VPDetectionOperator(bpy.types.Operator):
    bl_idname = "view3d.vp_detection"
    bl_label = "VP detection"
    bl_description = "Automatic camera calibration based on an image."

    def execute(self,context):
        
        import os
        import bpy
        from bpy.utils import register_class
        from bpy.utils import unregister_class
        import mathutils
        from mathutils import Vector
        from math import sqrt, pi, atan2, degrees
        import cv2
        import numpy as np
        from itertools import combinations
        from lu_vp_detect import VPDetection
        import argparse
        import bmesh
        import math
        from . import intersection
        from . import calibration
        from . import operator
        
        ### Set TOP camera view and create background image #############################
        
        # Get the default image
        img = 'D:\\(D)Files\\Politecnico\\Polito\\Grafica\\Progetto\\AddOn\\test_image.jpg'

        # Get the image path
        cwd = os.getcwd()
        
        img=bpy.context.scene['image_filepath']
        print('path: ' + bpy.context.scene['image_filepath'])

        # Get the mesh database path

        database_path = f"{cwd}/Mesh database" 

        # Preparing the view

        bpy.ops.view3d.view_axis(type='TOP', align_active=False, relative=False)
        
        bpy.ops.object.load_background_image(filepath=img, filter_image=True, filter_folder=True, view_align=True)

        bpy.data.scenes["Scene"].render.use_freestyle=True
        bpy.data.scenes["Scene"].render.line_thickness=0.6

        ### VP Detection #################################################################

        length_thresh = 60
        principal_point = None
        focal_length = 1102.79
        seed = 1337

        print('Image path: '+img)

        vpd = VPDetection(length_thresh, principal_point, focal_length, seed)
        vps = vpd.find_vps(img)
        vp2d = vpd.vps_2D

        print('Detected VPs: ')
        print(vp2d)

        img=cv2.imread(img)

        img_x=img.shape[1]
        img_y=img.shape[0]

        print('img_x: ')
        print(img_x)
        print('img_y: ')
        print(img_y)

        ###Taking the 2D VPs' reference frame to the reference frame with the origin in the center of the image ####

        vp1 = vp2d[0]
        vp2 = vp2d[1]
        vp3 = vp2d[2]

        vp1[0] = vp1[0] - img_x/2
        vp1[1] = vp1[1] - img_y/2

        vp2[0] = vp2[0] - img_x/2
        vp2[1] = vp2[1] - img_y/2

        vp3[0] = vp3[0] - img_x/2
        vp3[1] = vp3[1] - img_y/2

        vp2d[0] = vp1
        vp2d[1] = vp2 
        vp2d[2] = vp3 

        print('VPs in the new reference frame')
        print(vp2d)

        ### Compute the scaling factor pixel(image)-metres(blender) ###################

        if(img_x>img_y):
            fattscala = img_x/5
        else:
            fattscala = img_y/5
            
        print('Scaling factor: ')
        print(fattscala)

        ### Convert the image cords in blender cords ######################################

        vp2d = vp2d/fattscala

        print('scaled VPs: ')
        print(vp2d)

        vp1 = vp2d[0]
        vp2 = vp2d[1]
        vp3 = vp2d[2]

        print('Creation of the Vps mesh...')

        mesh = bpy.data.meshes.new("vp2d")  # add the new mesh
        obj = bpy.data.objects.new(mesh.name, mesh)
        col = bpy.data.collections.get("Collection")
        col.objects.link(obj)
        bpy.context.view_layer.objects.active = obj

        verts = [
                 ( vp1[0],  vp1[1],  0.0), 
                 ( vp2[0],  vp2[1],  0.0), 
                 ( vp3[0],  vp3[1],  0.0), 
                ]  # 3 verts made with XYZ coords
        edges = []
        faces = []

        mesh.from_pydata(verts, edges, faces)

        ### Find the verts of the perspective lines (one at 30°, the other at -30°) ##########

        vb1 = verts[0]
        vb1 = np.asarray(vb1)
        vb1[0] = vb1[0] + math.sin(30)
        vb1[1] = vb1[1] + math.cos(30)

        vb2 = verts[0]
        vb2 = np.asarray(vb2)
        vb2[0] = vb2[0] + math.sin(-30)
        vb2[1] = vb2[1] + math.cos(-30)

        ### Find the verts of the perspective lines (one at 90°, the other based
        ### oh the other vanishing point) ########################################

        vc1 = verts[2]
        vc1 = np.asarray(vc1)
        vc1[1] = vc1[1]+1

        vc2 = verts[0]
        vc2 = list(vc2)
        vc2[0] = vc2[0]-1

        vc3 = verts[1]
        vc3 = list(vc3)
        vc3[0] = vc3[0]+1

        ### Find the verts of the rectangle

        B = [intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc2)[0], intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc2)[1], 0.0]
        A = [intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc1)[0], intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc1)[1], 0.0]
        C = [intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc2)[0], intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc2)[1], 0.0]
        D = [intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc1)[0], intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc1)[1], 0.0]

        print("A:")
        print(A)

        print("vb1:")
        print(vb1)

        ### Find the dangling verts

        F = [intersection.intersect_2d(np.asarray(verts[1]),A,np.asarray(verts[2]),vc3)[0], intersection.intersect_2d(np.asarray(verts[1]),A,np.asarray(verts[2]),vc3)[1], 0.0]
        E = [intersection.intersect_2d(np.asarray(verts[1]),D,np.asarray(verts[2]),vc3)[0], intersection.intersect_2d(np.asarray(verts[1]),D,np.asarray(verts[2]),vc3)[1], 0.0]

        rect_verts=[B,A,C,D,F,E]
        
        print('Verts of the rectangle: ')
        print(rect_verts)

        edges = [[1,4],[3,5]]
        faces = [[0,1,3,2]]

        ### Create rectangle mesh ##################################################

        print('Creation of the rectangle...')

        mesh = bpy.data.meshes.new("rectangle")  # add the new mesh
        obj = bpy.data.objects.new(mesh.name, mesh)
        col = bpy.data.collections.get("Collection")
        col.objects.link(obj)
        bpy.context.view_layer.objects.active = obj

        mesh.from_pydata(rect_verts, edges, faces)

        print('Rectangle created.')

        ### Select the rectangle only, in order to make the camera calibration module to work 
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        ### Start camera calibration based on the rectangle (active object) #################
        print('Calibrating camera...')
        bpy.ops.camera.camera_calibration_fxy_pr_vv()
    
        bpy.ops.object.select_all(action='DESELECT')

        for ob in bpy.data.objects:
            if ob != bpy.data.objects["Camera"] and ob != bpy.data.objects["Light"]:
                ob.select_set(True)
        bpy.ops.object.delete()
        
        
        bpy.data.objects["Camera"].select_set(True)
        bpy.ops.view3d.snap_cursor_to_center()
        bpy.ops.view3d.snap_selected_to_cursor()
        bpy.ops.transform.rotate(value=math.radians(90), orient_axis='X')
        bpy.ops.transform.rotate(value=math.radians(90), orient_axis='Z')

        return {'FINISHED'}