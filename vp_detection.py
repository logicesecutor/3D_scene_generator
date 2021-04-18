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
        from PIL import Image, ExifTags
        import numpy as np
        from itertools import combinations
        from lu_vp_detect import VPDetection
        import argparse
        import bmesh
        import math
        from . import intersection
        from . import calibration
        from . import operator
        
        print('\n---------- VP DETECTION ----------')

        ### Set TOP camera view and create background image #############################
        
        # Get the image path
        cwd = os.getcwd()
        
        img_path=bpy.context.scene['image_filepath']
        print('path: ' + bpy.context.scene['image_filepath'])

        # Get the mesh database path

        database_path = f"{cwd}/Mesh database" 

        # Preparing the view

        bpy.data.cameras['Camera'].background_images.clear()

        bpy.ops.view3d.view_axis(type='TOP', align_active=False, relative=False)
        
        bpy.ops.object.load_background_image(filepath=img_path, filter_image=True, filter_folder=True, view_align=True)

        bpy.data.scenes["Scene"].render.use_freestyle=True
        bpy.data.scenes["Scene"].render.line_thickness=0.6

        ### VP Detection #################################################################

        img_pil = Image.open(img_path)
        img_exif = img_pil.getexif()
        focal_length = 1102.79

        if img_exif is not None:
            print('\nThis image has exif data.\n')
            for key, val in img_exif.items():
                if key in ExifTags.TAGS:
                    print(f'{ExifTags.TAGS[key]}:{val}')
                    #if key == 'FocalLenght':
                        #focal_length = val
        else:
            print('\nThis image has no exif data.\n')

        length_thresh = 60
        principal_point = None
        
        seed = 1337

        print('\nImage path: '+img_path)

        vpd = VPDetection(length_thresh, principal_point, focal_length, seed)
        vps = vpd.find_vps(img_path)
        vp2d = vpd.vps_2D

        print('Detected VPs: ')
        print(vp2d)

        img=cv2.imread(img_path)

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

        ### Prevent exceeding Blender unit ################################################

        for i in vp2d:
            for j in i:
                if j>9999: 
                    j=9999

        vp1 = vp2d[0]
        vp2 = vp2d[1]
        vp3 = vp2d[2]

        if vp1[0]<vp2[0]:

            tmp = vp1
            vp1 = vp2
            vp2 = tmp

        vp2d[0] = vp1
        vp2d[1] = vp2
        vp2d[2] = vp3

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

        if verts[0][0]>2.5:
            vb1 = [0,2.5,0]
            vb2 = [0,-2.5,0]
        else:
            vb1 = verts[0]
            vb1 = np.asarray(vb1)
            vb1[0] = vb1[0] + math.sin(60)
            vb1[1] = vb1[1] + math.cos(60)

            vb2 = verts[0]
            vb2 = np.asarray(vb2)
            vb2[0] = vb2[0] + math.sin(-60)
            vb2[1] = vb2[1] + math.cos(-60)
                   

        ### Find the verts of the perspective lines (one at 90°, the other based
        ### on the other vanishing point) ########################################

        vc1 = [0,-2.5,0] if verts[2][1]<0 else [0,2.5,0]
        # vc1 = verts[2]
        # vc1 = np.asarray(vc1)
        # vc1[1] = vc1[1]+0.001 if verts[2][1]<0 else vc1[1]-0.001

        vc2 = verts[0]
        vc2 = list(vc2)
        #vc2[0] = verts[0][0]/2 - 1
        vc2[0] = 2.5 if verts[0][0]>2.5 else verts[0][0] - 0.01

        vc3 = verts[1]
        vc3 = list(vc3)
        #vc3[0] = verts[1][0] + 1
        vc3[0] = -2.5 if verts[1][0]<-2.5 else verts[1][0] + 0.01

        ### Find the verts of the rectangle ##################################################

        B = [intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc2)[0], intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc2)[1], 0.0]
        A = [intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc1)[0], intersection.intersect_2d(np.asarray(verts[0]),vb1,np.asarray(verts[2]),vc1)[1], 0.0]
        C = [intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc2)[0], intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc2)[1], 0.0]
        D = [intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc1)[0], intersection.intersect_2d(np.asarray(verts[0]),vb2,np.asarray(verts[2]),vc1)[1], 0.0]

        if A[0]>B[0]:

            tmp = A
            A = B
            B = tmp

            tmp = C
            C = D
            D = tmp

        #Prevent parallel edges
        if B[0] <= C[0]+0.001 and B[0] >= C[0]-0.001:
            B[0] = B[0]+0.002 if verts[2][0]<vc2[0] and verts[2][1]>0 else B[0]-0.002

        if B[1] <= C[1]+0.001 and B[1] >= C[1]-0.001:
            B[1] = B[1]+0.002 

        if A[1] <= D[1]+0.001 and A[1] >= D[1]-0.001:
            A[1] = A[1]+0.002

        ### Find the dangling verts ##################################################

        F = [intersection.intersect_2d(np.asarray(verts[1]),A,np.asarray(verts[2]),vc3)[0], intersection.intersect_2d(np.asarray(verts[1]),A,np.asarray(verts[2]),vc3)[1], 0.0]
        E = [intersection.intersect_2d(np.asarray(verts[1]),D,np.asarray(verts[2]),vc3)[0], intersection.intersect_2d(np.asarray(verts[1]),D,np.asarray(verts[2]),vc3)[1], 0.0]

        #Prevent parallel edges
        if F[1] <= E[1]+0.001 and F[1] >= E[1]-0.001:
            F[1] = F[1]+0.002
            
        if F[0] <= E[0]+0.001 and F[0] >= E[0]-0.001:
            F[0] = F[0]-0.002 if verts[2][0]<vc2[0] else F[0]+0.002

        print("C: "+str(C) + "\nB: "+str(B))
        print("A: "+str(A) + "\nD: "+str(D))
        print("F: "+str(F) + "\nE: "+str(E))

        mesh = bpy.data.meshes.new("rectangle")
        obj = bpy.data.objects.new("rectangle", mesh)

        scene = bpy.context.scene
        col = bpy.data.collections.get("Collection")
        col.objects.link(obj)
        bpy.context.view_layer.objects.active = obj  # set as the active object in the scene
        obj.select_set(True)  # select object

        bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit

        bm = bmesh.from_edit_mesh(mesh)

        A_vert = bm.verts.new(A)
        B_vert = bm.verts.new(B)
        C_vert = bm.verts.new(C)
        D_vert = bm.verts.new(D)

        E_vert = bm.verts.new(E)
        F_vert = bm.verts.new(F)

        bmesh.update_edit_mesh(mesh, False, True)

        bpy.ops.mesh.select_all(action='SELECT')
        E_vert.select = False
        F_vert.select = False

        bpy.ops.mesh.edge_face_add()

        bpy.ops.mesh.select_all(action='DESELECT')

        A_vert.select = True
        F_vert.select = True

        bpy.ops.mesh.edge_face_add()

        bpy.ops.mesh.select_all(action='DESELECT')

        D_vert.select = True
        E_vert.select = True

        bpy.ops.mesh.edge_face_add()

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #edit

        # rect_verts=[B,A,C,D,F,E]
        
        # print('Verts of the rectangle: ')
        # print(rect_verts)

        # edges = [[1,4],[3,5]]
        # faces = [[0,1,3,2]]

        # ### Create rectangle mesh ##################################################

        # print('Creation of the rectangle...')

        # mesh = bpy.data.meshes.new("rectangle")  # add the new mesh
        # obj = bpy.data.objects.new(mesh.name, mesh)
        # col = bpy.data.collections.get("Collection")
        # col.objects.link(obj)
        # bpy.context.view_layer.objects.active = obj

        # mesh.from_pydata(rect_verts, edges, faces)

        print('Rectangle created.')

        ### Select the rectangle only, in order to make the camera calibration module to work  ###

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        ### Start camera calibration based on the rectangle (active object) #################
        print('\n---------- CAMERA CALIBRATION ----------')
        
        bpy.ops.camera.camera_calibration_fxy_pr_vv()
    
        bpy.ops.object.select_all(action='DESELECT')

        for ob in bpy.data.objects:
            if ob != bpy.data.objects["Camera"] and ob != bpy.data.objects["Light"]:
                ob.select_set(True)
        bpy.ops.object.delete()
        
        ### Normalize the camera orientation ##################################

        bpy.data.objects["Camera"].select_set(True)
        bpy.ops.view3d.snap_cursor_to_center()
        bpy.ops.view3d.snap_selected_to_cursor()
        
        ### Detect the orientation of the room from camera and normalize again #################

        if bpy.data.objects["Camera"].rotation_euler[1]>0:
            bpy.ops.transform.rotate(value=math.radians(90), orient_axis='Y')
        else:
            bpy.ops.transform.rotate(value=math.radians(-90), orient_axis='Y')

        camera=bpy.context.scene.camera
        camera_rot=camera.matrix_world.to_3x3() @ Vector((0,0,-1))

        print(camera_rot)

        room_orient=[False,False]

        room_orient[0]=False if camera_rot[0]<0 else True
        room_orient[1]=False if camera_rot[1]<0 else True

        i=0

        while (room_orient[0] != True and room_orient[1] != True) or i >= 3:
            bpy.ops.transform.rotate(value=math.radians(90), orient_axis='Z')
            i = i+1

        bpy.ops.transform.rotate(value=math.radians(90), orient_axis='Z')

        return {'FINISHED'}