import bpy
import bmesh
import os
from mathutils import Matrix
from mathutils import Vector


class RoomOperator(bpy.types.Operator):
    bl_idname = "view3d.room"
    bl_label = "room generation"
    bl_description = "Generates a room basing on the position of the objects."

    def execute(self, context):

        print('----------ROOM GENERATION----------')

        bpy.ops.screen.animation_cancel()
        bpy.ops.screen.frame_jump(end=False)

        ground_z = 0
        wall_x = 0
        wall_y = 0
        bpy.ops.object.select_all(action='DESELECT')

        #Detect the orientation of the room from camera
        camera=bpy.context.scene.camera
        camera_rot=camera.matrix_world.to_3x3() @ Vector((0,0,-1))

        room_orient=[False,False]

        room_orient[0]=False if camera_rot[0]<0 else True
        room_orient[1]=False if camera_rot[1]<0 else True

        print(room_orient)

        for obj in bpy.data.objects:
            
            if obj != bpy.data.objects["Camera"] and obj != bpy.data.objects["Light"]:

                if obj.name=='room' or obj.name=='grass' or obj.name=='blade':
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    bpy.ops.object.delete()
                
                else:

                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    
                    extern = computeExternVert(obj,'GLOBAL',room_orient)
                    lowest_z = extern[2]
                    x_max = extern[0]
                    y_max = extern[1]

                    #print(obj.name+" lowest vert: "+ str(lowest_z))
                    print(obj.name+" x_max: "+ str(x_max))
                    print(obj.name+" y_max: "+ str(y_max))                
                    
                    if lowest_z < ground_z:
                        ground_z = lowest_z
                        #print("new ground_z: " + str(ground_z))

                    if x_max > wall_x and room_orient[0]==True:
                        wall_x = x_max
                        print("new wall_x: " + str(wall_x))

                    if x_max < wall_x and room_orient[0]==False:
                        wall_x = x_max
                        print("new wall_x: " + str(wall_x))   
                    
                    if y_max > wall_y and room_orient[1]==True:
                        wall_y = y_max
                        print("new wall_y: " + str(wall_y))
                    
                    if y_max < wall_y and room_orient[1]==False:
                        wall_y = y_max
                        print("new wall_y: " + str(wall_y))

                    #tolgo la edit mode e deseleziono l'oggetto
                    bpy.ops.object.editmode_toggle()
                    obj.select_set(False)

        wall_x = wall_x-5 +0.05 if room_orient[0]==True else wall_x+5 -0.05
        wall_y = wall_y-5 +0.05 if room_orient[1]==True else wall_y+5 -0.05
        lowest_z = lowest_z - 0.1

        #importo il pavimento, attento al percorso
        # Getting Current Working Directory
        cwd = os.getcwd()
        database_path = f"{cwd}/Mesh database"  

        bpy.ops.wm.append(
                    directory=database_path,
                    filename="entire_collection.blend\\Object\\room")

        room_obj=bpy.context.scene.objects["room"]
        bpy.context.view_layer.objects.active = room_obj
        #porto il pavimento alla z minima
        bpy.ops.transform.translate(value=(0, 0, ground_z))

        #salvo i lati del pavimento
        room_me = room_obj.data
        room_edges = room_me.edges

        bpy.ops.object.editmode_toggle() #edit
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle() #object

        #creo le pareti su wall_x e wall_y
        room_edges[3 if room_orient[1]==True else 1].select = True
        bpy.ops.object.editmode_toggle() #edit
        bpy.ops.transform.translate(value=(0, wall_y, 0), constraint_axis=(False, True, False), mirror=True)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle() #object
        room_edges[2 if room_orient[0]==True else 0].select = True
        bpy.ops.object.editmode_toggle() #edit
        bpy.ops.transform.translate(value=(wall_x, -0, -0), constraint_axis=(True, False, False), mirror=True)
        bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, 5), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle() #object
        room_edges[3 if room_orient[1]==True else 1].select = True
        bpy.ops.object.editmode_toggle() #edit
        bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, 5), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle() #object

        bpy.ops.screen.animation_play()
        return {'FINISHED'}

def computeExternVert(obj, space, room_orient):
    # edit mode per selezionare vertici
    bpy.ops.object.editmode_toggle()

    #space = 'LOCAL' or 'GLOBAL'
    TOL = 1e-7
    M = obj.matrix_world if space == 'GLOBAL' else Matrix()
    me = obj.data

    bm = bmesh.from_edit_mesh(me)
    
    verts0 = sorted(bm.verts, key=lambda v: (M @ v.co).x)
    verts1 = sorted(bm.verts, key=lambda v: (M @ v.co).y)
    verts2 = sorted(bm.verts, key=lambda v: (M @ v.co).z)

    bm.select_flush(False)
    #bm.select_flush_mode()
    
    x = (M @ verts0[0 if room_orient[0]==False else -1].co).x
    y = (M @ verts1[0 if room_orient[1]==False else -1].co).y
    z = (M @ verts2[0].co).z
    bmesh.update_edit_mesh(me)

    #ritorno i vertici esterni
    return [x,y,z]