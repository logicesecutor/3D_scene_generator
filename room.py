import bpy
import bmesh
import os
from mathutils import Matrix
from mathutils import Vector
from math import radians, sin
import collections
import operator



class Forniture():

    MEDIUM_threshold = 0.7
    HIGH_Threshold = 1.5

    def __init__(self, obj, ground_z, onWall, floating, support):

        self.objRef = obj

        self.onWall = onWall
        self.isFloating = floating
        self.support = support
        self.high = self.defineObjHigh(ground_z)

        self.collision_objects = []
        self.interaction_objects = []
        self.collision_radius = max(obj.dimensions * 0.5) * 1.2
        self.interaction_radius = max(obj.dimensions * 0.5) * 5

        self.nearest_wall = None

        if not self.support:
            self.objAbove = []

        
    def collision_object_list(self, fornitures):
        nearest=[]
        for obj in fornitures:
            if obj.objRef != self.objRef:
                direction = self.objRef.location - obj.objRef.location
                magnitude = direction.magnitude
                if magnitude < self.colllision_radius:
                    nearest.append(
                        {
                            "fornitureRef": obj, 
                            "magnitude": magnitude,
                            "direction": direction,
                        }
                    )
        # Actually I'm sorting from nearest to farther
        nearest.sort(key= lambda x: x["magnitude"])

        self.collision_objects = nearest


    def nearest_object_list(self, fornitures):
        nearest=[]
        for obj in fornitures:
            if obj.objRef != self.objRef:
                direction = self.objRef.location - obj.objRef.location
                magnitude = direction.magnitude
                if magnitude < self.interaction_radius:
                    
                    nearest.append(
                        {
                            "fornitureRef": obj, 
                            "magnitude": magnitude,
                            "direction": direction,
                        }
                    )

        # Actually I'm sorting from nearest to farther
        nearest.sort(key= lambda x: x["magnitude"])

        self.interaction_objects = nearest

    
    def isFree(self):
        
        if not self.support: 
            print("Function not defined for this object")
            return
        
        return len(self.objAbove) > 2




    def collide(self):

        return self.collision_objects != []


    def nearest_wall_location(self, walls):

        nearest_wall = float('inf')

        for wall in walls:
            angle = self.objRef.location.angle(wall)
            dist = sin(angle) * self.objRef.location.resized(2).magnitude
            #dist = (wall.location - self.objRef.location).magnitude
            if dist < nearest_wall:
                nearest_wall = dist
                save_wall = wall

        self.nearest_wall = save_wall


    def defineObjHigh(self, ground_z):

        if self.objRef.location.z - ground_z > self.HIGH_Threshold:
            return "h"
        elif self.objRef.location.z - ground_z > self.MEDIUM_threshold:
            return "m"
        else:
            return "l"

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
        occurrencies = {}

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


        # New Version 
        # ================================================================
        print ('\nSearching for floating objects...')
        # ================================================================

        walls = [Vector((greatest_x, 0, 0)), Vector((0, greatest_y, 0))]
    
        non_floating_obj_category = ("Camera","Light","bed","chair","dining table","toilet","shelf","bedside table","refrigerator","grass","blade","room","blanket","smoke")
        onWall_obj_category = ("television", "shelf")
        support_obj_category = ("bed", "chair", "dining table", "grass", "ground", "bedside table")

        fornitures = []
        for obj in bpy.context.scene.objects:
            if not obj.name.startswith(non_floating_obj_category):
                fornitures.append(
                    Forniture(obj,
                            ground_z,
                            onWall=obj.name.startswith(onWall_obj_category), 
                            floating= not obj.name.startswith(non_floating_obj_category), 
                            support= obj.name.startswith(support_obj_category),
                            )
                )

        #creo tavolini e mensole sotto gli oggetti a mezz'aria, se non già presenti
        print ('\nSearching for floating objects...')
        for obj in fornitures:
            if obj.isFloating:
                if obj.high == "m":
                    support = "table"
                    print (str(obj.objRef.name)+' will need a dining table/bedside table')

                elif obj.high == "h":
                    support = "shelf" 
                    print (str(obj.objRef.name)+' will need a shelf')
                else:
                    support = "ground"
                    print (str(obj.objRef.name)+' is close to the ground')

                putSupport(support, fornitures, ground_z, walls, obj, database_path, occurrencies)  # FUTURE VERSIONS: LIST OF OBJECT WHICH CAN BE USED AS SUPPORT

                
                

            # for obj in bpy.data.objects:
                # if not obj.name.startswith(("Camera","Light","bed","chair","dining table","toilet","shelf","bedside table","refrigerator","grass","blade","room","blanket","smoke")): 
                
                    # if obj.objRef.location.z - ground_z > 0.7 and (objects[obj.name])[2]-ground_z < 1.5:
                    #     (objects[obj.name])[3] = 1 #will need a dining table/bedside table
                    #     print (str(obj.name)+' will need a dining table/bedside table')
                    # elif (objects[obj.name])[2]-ground_z > 1.5:
                    #     (objects[obj.name])[3] = 2 #will need a shelf
                    #     print (str(obj.name)+' will need a shelf')
                    # else:
                    #     objects.pop(obj.name)
                    #     print (str(obj.name)+' is close to the ground')


        # print ('\nSearching for surfaces below floating objects...')
        # array=[None]*len(objects)
        # i=0
        # for floating in objects:
        #     array[i] = objects[floating][2]
        #     i=i+1

        
        # array.sort()

        # i=0
        # while i<len(objects):

        #     floating=getFloatingObject(array[i],objects)

        #     pos=bpy.data.objects[floating].location
        #     print('\n'+floating +' position: '+str(pos))
            
        #     for obj in bpy.context.scene.objects:
        #         if obj.name.startswith(("chair","dining table","shelf","bedside table","bed")):
        #         #Controllo che non siano già sotto gli oggetti a mezz'aria, altrimenti li aggiungo

        #             topbb = computeExternVert(obj,'GLOBAL',room_orient,True)
        #             print(obj.name +' topbb: '+str(topbb))
                
        #             if pos[0]<topbb[0] and pos[0]>topbb[2] and pos[1]>topbb[3] and pos[1]<topbb[1] and objects[floating][3] < 2: #vertice più alto
        #                 objects[floating][3]=0
        #                 print (str(floating)+' has already a '+str(obj.name)+' below. Set not floating')
        #                 break
            
        #     bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object
        #     bpy.ops.object.select_all(action='DESELECT')

        #     if objects[floating][3]==2:

        #         if pos[0]-greatest_x < pos[1]-greatest_y:
                    
        #             if not floating.startswith("tv"):

        #                 bpy.ops.wm.append(
        #                     directory=database_path,
        #                     filename="entire_collection.blend\\Object\\shelf")

        #                 bpy.ops.transform.rotate(value=radians(90), constraint_axis=(False, False, True))
        #                 bpy.ops.transform.translate(value=(greatest_x,pos[1],objects[floating][2]-0.5))
                        
        #                 bpy.data.objects[floating].location[0] = greatest_x-0.3

        #                 print ('Added a shelf below '+str(floating))

        #             else:
                        
        #                 bpy.ops.wm.append(
        #                         directory=database_path,
        #                         filename="entire_collection.blend\\Collection\\tv alt")

        #                 bpy.ops.transform.translate(value=(pos[0],greatest_y-0.1,pos[2]))

        #                 bpy.ops.object.select_all(action='DESELECT')
        #                 bpy.data.objects[floating].select_set(True)
        #                 bpy.ops.object.delete()
                        
        #                 print ('Moved tv to the wall')
                    
        #         else:

        #             if not floating.startswith("tv"):

        #                 bpy.ops.wm.append(
        #                     directory=database_path,
        #                     filename="entire_collection.blend\\Object\\shelf")

        #                 bpy.ops.transform.translate(value=(pos[0],greatest_y,objects[floating][2]-0.5))

        #                 bpy.data.objects[floating].location[1] = greatest_y-0.3
                        
        #                 print ('Added a shelf below '+str(floating))
                    
        #             else:

        #                 bpy.ops.wm.append(
        #                         directory=database_path,
        #                         filename="entire_collection.blend\\Collection\\tv alt")

        #                 bpy.ops.transform.rotate(value=radians(90), constraint_axis=(False, False, True))
        #                 bpy.ops.transform.translate(value=(greatest_x-0.1,pos[1],pos[2]))

        #                 bpy.ops.object.select_all(action='DESELECT')
        #                 bpy.data.objects[floating].select_set(True)
        #                 bpy.ops.object.delete()
                        
        #                 print ('Moved tv to the wall')
                    
        #     elif objects[floating][3]==1:
                
        #         bpy.ops.wm.append(
        #             directory=database_path,
        #             filename="entire_collection.blend\\Object\\dining table",
        #             autoselect=True)    #controlla per comodino

        #         bpy.ops.transform.translate(value=(pos[0],pos[1],objects[floating][2]-0.25)) 
        #         print('Added a dining table below '+floating)

        #     i=i+1                           

        # for obj in bpy.context.scene.objects:
        #     if obj.name.startswith(("chair","dining table","shelf","bedside table","bed")):
                
        #         if obj.location[0]+(obj.dimensions[0]/2) > greatest_x and not obj.name.startswith("shelf"):
                            
        #             obj.location[0]= greatest_x - obj.dimensions[0]/2
        #             print('Moved '+obj.name+' to avoid collision with wall_x')

        #         elif obj.location[0] > greatest_x and obj.name.startswith("shelf"):

        #             obj.location[0]= greatest_x 
        #             print('Moved '+obj.name+' to avoid collision with wall_x')

        #         if obj.location[1]+(obj.dimensions[1]/2) > greatest_y:

        #             obj.location[1]= greatest_y - obj.dimensions[1]/2
        #             print('Moved '+obj.name+' to avoid collision with wall_y')

        bpy.ops.screen.animation_play()
        return {'FINISHED'}


def putSupport(type: str, fornitures: list, ground_z, walls: list, forniture: Forniture, database_path, occurrencies):
    """
    Take the obj and try to put it on a object avoiding collision between objects
    If an object to be putted on a shelf has collisions
    search for nearest object which have a support attribute.
    If not put a support avoiding collision
    """
    # Between the nearest objects find if someone is a support and if have free space available 
    forniture.nearest_object_list(fornitures)

    find = False
    for obj in forniture.interaction_objects:
        f = obj["fornitureRef"]
        if f.support and f.isFree():

            forniture.objRef.location.z = f.objRef.location.z + 0.5
            f.objAbove.append(forniture)
            forniture.isFloating = False

            find = True
            break

    if not find:

        bpy.ops.object.select_all(action='DESELECT')

        if type == "shelf":
            onWall = True
            floating = False

            bpy.ops.wm.append(
                            directory=database_path,
                            filename="entire_collection.blend\\Object\\shelf",
                            )
            
            bpy.ops.transform.rotate(value=radians(90), constraint_axis=(False, False, True))

        elif type == "table":
            onWall = True
            floating = False

            bpy.ops.wm.append(
                            directory=database_path,
                            filename="entire_collection.blend\\Object\\dining table",
                            )
            
        elif type=="ground":
            print("Putted on the ground")
            forniture.isFloating=False
            return
        else:
            print("TBI supporter = createOther()")
            return
        

        # Retrieve the object Reference
        if type in occurrencies.keys():
            occurrencies[type] += 1
        else:
            occurrencies[type] = 0


        bpy.context.view_layer.objects.active = bpy.data.objects[type]
        ref = bpy.context.object
        ref.name = f"{type}"+ ".%03d" % (occurrencies[type])

        # Wrapping the new support in a forniture class
        bpy.ops.transform.rotate(value=radians(90), constraint_axis=(False, False, True))
        if forniture.objRef.location.x - greatest_x < forniture.objRef.location.y - greatest_y:
            bpy.ops.transform.translate(value=(walls[0].x, forniture.objRef.location.y, forniture.objRef.location.z - 0.5))
        else:
            bpy.ops.transform.translate(value=(forniture.objRef.location.y, walls[1].y , forniture.objRef.location.z - 0.5))
        
        # TODO: PARENTING
        #bpy.ops.transform.translate(value=(forniture.objRef.location.x, forniture.objRef.location.y, forniture.objRef.location.z - 0.5) )

        newSupport = Forniture( ref, ground_z, onWall, floating, True)

        #newSupport.nearest_wall_location(walls)
        #newSupport.nearest_object_list(fornitures)
        newSupport.collision_object_list(fornitures)

        #wall = forniture.objRef.location.dot(newSupport.nearest_wall)
        
        if newSupport.collide():
            final_dir = Vector((.0, .0, .0))
            for obj in newSupport.collision_objects:
                final_dir += obj["direction"]
            
            # Computed final direction and move the object enough, in that direction, 
            # to push away the nearest object
            newSupport.objRef.location += final_dir.normalize() * (interaction_radius - newSupport.near_objects[0]["magnitude"])
            newSupport.objAbove.append(forniture)

            #TODO: veryfy if the new position excede the walls boundary
            #.....

        else:
            forniture.objRef.location = newSupport.objRef.location + 0.5
            newSupport.objAbove.append(forniture)

    fornitures.append(newSupport)


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