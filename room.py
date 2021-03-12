import bpy
import bmesh
import os
from mathutils import Matrix
from mathutils import Vector
from math import radians
import collections
import operator

class RoomOperator(bpy.types.Operator):
    bl_idname = "view3d.room"
    bl_label = "room generation"
    bl_description = "Generates a room basing on the position of the objects."

    def execute(self, context):

        print('\n----------ROOM GENERATION----------\n')

        bpy.ops.screen.animation_cancel()
        bpy.ops.screen.frame_jump(end=False)

        objects={}
        ground_z = 0
        greatest_x = 0
        greatest_y = 0
        bpy.ops.object.select_all(action='DESELECT')

        #Detect the orientation of the room from camera
        camera=bpy.context.scene.camera
        camera_rot=camera.matrix_world.to_3x3() @ Vector((0,0,-1))

        room_orient=[False,False]

        room_orient[0]=False if camera_rot[0]<0 else True
        room_orient[1]=False if camera_rot[1]<0 else True

        for obj in bpy.data.objects:
            
            if obj != bpy.data.objects["Camera"] and obj != bpy.data.objects["Light"]:

                if obj.name=='room' or obj.name=='grass' or obj.name=='blade':
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    bpy.ops.object.delete()
                
                else:

                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    
                    extern = computeExternVert(obj,'GLOBAL',room_orient, False)
                    lowest_z = extern[2]
                    x_max = extern[0]
                    y_max = extern[1]

                    if not obj.name.startswith(("Camera","Light","bed","chair","dining table","toilet","shelf","bedside table","refrigerator","grass","blade","room","blanket","smoke")):
                        objects[obj.name] = [x_max, y_max, lowest_z, 0] #assume the object is not floating

                    #print(obj.name+" lowest vert: "+ str(lowest_z))
                    print(obj.name+" x_max: "+ str(x_max))
                    print(obj.name+" y_max: "+ str(y_max))                
                    
                    if lowest_z < ground_z:
                        ground_z = lowest_z
                        print("new ground_z: " + str(ground_z))

                    if x_max > greatest_x and room_orient[0]==True:
                        greatest_x = x_max
                        print("new greatest_x: " + str(greatest_x))

                    if x_max < greatest_x and room_orient[0]==False:
                        greatest_x = x_max
                        print("new greatest_x: " + str(greatest_x))   
                    
                    if y_max > greatest_y and room_orient[1]==True:
                        greatest_y = y_max
                        print("new greatest_y: " + str(greatest_y))
                    
                    if y_max < greatest_y and room_orient[1]==False:
                        greatest_y = y_max
                        print("new greatest_y: " + str(greatest_y))

                    #tolgo la edit mode e deseleziono l'oggetto
                    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                    obj.select_set(False)

                    print('\n')

        wall_x = greatest_x-5 +0.05 if room_orient[0]==True else greatest_x+5 -0.05
        wall_y = greatest_y-5 +0.05 if room_orient[1]==True else greatest_y+5 -0.05
        ground_z = ground_z - 0.1

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

        bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object

        #creo le pareti su wall_x e wall_y
        room_edges[3 if room_orient[1]==True else 1].select = True
        bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit
        bpy.ops.transform.translate(value=(0, wall_y, 0), constraint_axis=(False, True, False), mirror=True)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object
        room_edges[2 if room_orient[0]==True else 0].select = True
        bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit
        bpy.ops.transform.translate(value=(wall_x, -0, -0), constraint_axis=(True, False, False), mirror=True)
        bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, 5), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object
        room_edges[3 if room_orient[1]==True else 1].select = True
        bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit
        bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, 5), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object

        #creo tavolini e mensole sotto gli oggetti a mezz'aria, se non già presenti
        print ('\nSearching for floating objects...')
        for obj in bpy.data.objects:
            if not obj.name.startswith(("Camera","Light","bed","chair","dining table","toilet","shelf","bedside table","refrigerator","grass","blade","room","blanket","smoke")): 
                
                if (objects[obj.name])[2]-ground_z > 0.7 and (objects[obj.name])[2]-ground_z < 1.5:
                    (objects[obj.name])[3] = 1 #will need a dining table/bedside table
                    print (str(obj.name)+' will need a dining table/bedside table')
                elif (objects[obj.name])[2]-ground_z > 1.5:
                    (objects[obj.name])[3] = 2 #will need a shelf
                    print (str(obj.name)+' will need a shelf')
                else:
                    objects.pop(obj.name)
                    print (str(obj.name)+' is close to the ground')


        print ('\nSearching for surfaces below floating objects...')
        array=[None]*len(objects)
        i=0
        for floating in objects:
            array[i] = objects[floating][2]
            i=i+1
        
        array.sort()

        i=0
        while i<len(objects):

            floating=getFloatingObject(array[i],objects)

            pos=bpy.data.objects[floating].location
            print('\n'+floating +' position: '+str(pos))
            
            for obj in bpy.context.scene.objects:
                if obj.name.startswith(("chair","dining table","shelf","bedside table","bed")):
                #Controllo che non siano già sotto gli oggetti a mezz'aria, altrimenti li aggiungo

                    topbb = computeExternVert(obj,'GLOBAL',room_orient,True)
                    print(obj.name +' topbb: '+str(topbb))
                
                    if pos[0]<topbb[0] and pos[0]>topbb[2] and pos[1]>topbb[3] and pos[1]<topbb[1]: #vertice più alto
                        objects[floating][3]=0
                        print (str(floating)+' has already a '+str(obj.name)+' below. Set not floating')
                        break
            
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object
            bpy.ops.object.select_all(action='DESELECT')

            if objects[floating][3]==2:

                if pos[0]-greatest_x < pos[1]-greatest_y:
                    
                    if not floating.startswith("tv"):

                        bpy.ops.wm.append(
                            directory=database_path,
                            filename="entire_collection.blend\\Object\\shelf")

                        bpy.ops.transform.rotate(value=radians(90), constraint_axis=(False, False, True))
                        bpy.ops.transform.translate(value=(greatest_x,pos[1],objects[floating][2]-0.5))
                        
                        bpy.data.objects[floating].location[0] = greatest_x-0.3

                        print ('Added a shelf below '+str(floating))

                    else:
                        
                        bpy.ops.wm.append(
                                directory=database_path,
                                filename="entire_collection.blend\\Collection\\tv alt")

                        bpy.ops.transform.translate(value=(pos[0],greatest_y-0.1,pos[2]))

                        bpy.ops.object.select_all(action='DESELECT')
                        bpy.data.objects[floating].select_set(True)
                        bpy.ops.object.delete()
                        
                        print ('Moved tv to the wall')
                    
                else:

                    if not floating.startswith("tv"):

                        bpy.ops.wm.append(
                            directory=database_path,
                            filename="entire_collection.blend\\Object\\shelf")

                        bpy.ops.transform.translate(value=(pos[0],greatest_y,objects[floating][2]-0.5))

                        bpy.data.objects[floating].location[1] = greatest_y-0.3
                        
                        print ('Added a shelf below '+str(floating))
                    
                    else:

                        bpy.ops.wm.append(
                                directory=database_path,
                                filename="entire_collection.blend\\Collection\\tv alt")

                        bpy.ops.transform.rotate(value=radians(90), constraint_axis=(False, False, True))
                        bpy.ops.transform.translate(value=(greatest_x-0.1,pos[1],pos[2]))

                        bpy.ops.object.select_all(action='DESELECT')
                        bpy.data.objects[floating].select_set(True)
                        bpy.ops.object.delete()
                        
                        print ('Moved tv to the wall')
                    
            elif objects[floating][3]==1:
                
                bpy.ops.wm.append(
                    directory=database_path,
                    filename="entire_collection.blend\\Object\\dining table",
                    autoselect=True)    #controlla per comodino

                bpy.ops.transform.translate(value=(pos[0],pos[1],objects[floating][2]-0.25)) 
                print('Added a dining table below '+floating)

            i=i+1                           

        for obj in bpy.context.scene.objects:
            if obj.name.startswith(("chair","dining table","shelf","bedside table","bed")):
                
                if obj.location[0]+(obj.dimensions[0]/2) > greatest_x and not obj.name.startswith("shelf"):
                            
                    obj.location[0]= greatest_x - obj.dimensions[0]/2
                    print('Moved '+obj.name+' to avoid collision with wall_x')

                elif obj.location[0] > greatest_x and obj.name.startswith("shelf"):

                    obj.location[0]= greatest_x 
                    print('Moved '+obj.name+' to avoid collision with wall_x')

                if obj.location[1]+(obj.dimensions[1]/2) > greatest_y:

                    obj.location[1]= greatest_y - obj.dimensions[1]/2
                    print('Moved '+obj.name+' to avoid collision with wall_y')

        bpy.ops.screen.animation_play()
        return {'FINISHED'}

def computeExternVert(obj, space, room_orient, surface):
    # edit mode per selezionare vertici
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #edit
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit

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
    
    if not surface:
        x = (M @ verts0[0 if room_orient[0]==False else -1].co).x
        y = (M @ verts1[0 if room_orient[1]==False else -1].co).y
        z = (M @ verts2[0].co).z
        k = (M @ verts2[-1].co).z #won't use this
        j = (M @ verts2[-1].co).z #won't use this
        bmesh.update_edit_mesh(me)
    else:
        x = (M @ verts0[-1].co).x
        z = (M @ verts0[0].co).x
        y = (M @ verts1[-1].co).y
        k = (M @ verts1[0].co).y
        j = (M @ verts2[-1].co).z
        bmesh.update_edit_mesh(me)

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object
    #ritorno i vertici esterni
    return [x,y,z,k,j]

def getFloatingObject(i,objects):
    for floating in objects:
        if(objects[floating][2]==i):
            return floating