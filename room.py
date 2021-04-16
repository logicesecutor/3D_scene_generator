import bpy
import bmesh
import os
from mathutils import Matrix
from mathutils import Vector
from math import radians, sin
import numpy as np
import collections
import operator


class Forniture():

    MEDIUM_threshold = 0.7
    HIGH_Threshold = 1.5

    def __init__(self, obj, ground_z, onWall, floating):

        self.objRef = obj

        self.onWall = onWall
        self.isFloating = floating

        self.max_x = max(bb[0] for bb in obj.bound_box)
        self.min_x = min(bb[0] for bb in obj.bound_box)
        self.max_y = max(bb[1] for bb in obj.bound_box)
        self.min_y = min(bb[1] for bb in obj.bound_box)
        self.max_z = max(bb[2] for bb in obj.bound_box)
        self.min_z = min(bb[2] for bb in obj.bound_box)
        
        self.high = self.defineObjHigh(ground_z)

        self.collision_objects = []
        self.interaction_objects = []

        # Consider a sphere around the object with a radius of an half the max dimension length
        self.collision_radius = max(obj.dimensions) * 0.5 * 1.2
        self.interaction_radius = 1 # METERS

        self.nearest_wall = None

        
    def collision_object_list(self, fornitures):

        collisions = []

        for obj in fornitures:
            if obj.objRef != self.objRef:

                direction = self.objRef.location - obj.objRef.location
                magnitude = direction.magnitude
                dist = self.collision_radius + obj.collision_radius - magnitude

                if dist > 0:
                    
                    collisions.append(
                        {
                            "fornitureRef": obj, 
                            "magnitude": magnitude,
                            "direction": direction.normalized() * dist,
                        }
                    )

        self.collision_objects = collisions


    def near_object_list(self, fornitures):
        nearest=[]
        for obj in fornitures:
            if obj.objRef != self.objRef:

                direction = self.objRef.location - obj.objRef.location
                magnitude = direction.magnitude
                dist = self.interaction_radius + obj.interaction_radius - magnitude

                if  magnitude < self.interaction_radius + obj.interaction_radius:
                    
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


    def collide(self):
        return len(self.collision_objects) != 0


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


    def solveCollision(self, fornitures):
        camera = bpy.context.scene.camera
        self.collision_object_list(fornitures)

        if self.collide():
            final_dir = Vector((.0, .0, .0))
            for obj in self.collision_objects:
                final_dir += obj["direction"]
            # if (np.linalg.inv(camera.matrix_world) @ self.objRef.matrix_world)[0][3] > 0:
            #     self.objRef.location.x += self.overlapping * 2
            # else


    def defineObjHigh(self, ground_z):

        if self.objRef.location.z - ground_z > self.HIGH_Threshold:
            return "h"
        elif self.objRef.location.z - ground_z > self.MEDIUM_threshold:
            return "m"
        else:
            return "l"


class Support(Forniture):

    def __init__(self, obj, ground_z, onWall, floating):
        super().__init__(obj, ground_z, onWall, floating)
        self.objAbove = [] 

        self.whatWall = None

        # If is near to the Y wall
        if self.objRef.dimensions.x > self.objRef.dimensions.y:
            dim_x = self.objRef.dimensions.x * 0.25

            self.availableLocation = [
                Vector((dim_x, 0, 0)),
                Vector((-dim_x, 0, 0)),
                ]
        else:
            dim_y = self.objRef.dimensions.y * 0.25

            self.availableLocation = [
                Vector((0, dim_y, 0)),
                Vector((0, -dim_y, 0)),
                ]

    def setWall(self, whatWall):
        self.whatWall = whatWall
        if whatWall =='y':
            # If is near to the Y wall
            if self.objRef.dimensions.x > self.objRef.dimensions.y:
                dim_x = self.objRef.dimensions.x * 0.25

                self.availableLocation = [
                    Vector((dim_x, 0, 0)),
                    Vector((-dim_x, 0, 0)),
                    ]
            else:
                dim_y = self.objRef.dimensions.y * 0.25

                self.availableLocation = [
                    Vector((0, dim_y, 0)),
                    Vector((0, -dim_y, 0)),
                    ]
        else:
            # If is near to the X wall
            if self.objRef.dimensions.x > self.objRef.dimensions.y:
                dim_x = self.objRef.dimensions.x * 0.25

                self.availableLocation = [
                    Vector((0, dim_x, 0)),
                    Vector((0, -dim_x, 0)),
                    ]
            else:
                dim_y = self.objRef.dimensions.y * 0.25

                self.availableLocation = [
                    Vector((dim_y, 0, 0)),
                    Vector((-dim_y, 0, 0)),
                    ]


    def putObjectAbove(self, forniture):
        forniture.objRef.location = self.objRef.location
        forniture.objRef.location += self.availableLocation.pop()

        # Setting the forniture on support and not floating anymore
        self.objAbove.append(forniture)
        forniture.isFloating = False


    def isFree(self):
        return len(self.availableLocation) > 0
        

    def divide(self):

        # TODO: find a general way to subdivide a mesh surface
        pass


    def collision_object_list(self, fornitures):
        
        collisions = []

        for obj in fornitures:
            if obj.objRef != self.objRef:

                if obj in self.objAbove:
                    continue

                direction = self.objRef.location - obj.objRef.location
                magnitude = direction.magnitude
                dist = self.collision_radius + obj.collision_radius - magnitude

                if dist > 0:
                    
                    collisions.append(
                        {
                            "fornitureRef": obj, 
                            "magnitude": magnitude,
                            "direction": direction.normalized() * dist,
                        }
                    )


        self.collision_objects = collisions



    def solveCollision(self, fornitures, walls=None):

        self.collision_object_list(fornitures)

        if self.collide():
            final_dir = Vector((.0, .0, .0))
            for obj in self.collision_objects:
                final_dir += obj["direction"]
        
            # Computed final direction and move the object enough, in that direction, 
            # to push away the nearest object
            # final_dir = final_dir * (newSupport.collision_radius - newSupport.collision_objects[0]["magnitude"])

            # Update the support position and each object above it
            self.objRef.location += final_dir
            for obj in self.objAbove:
                obj.objRef.location += final_dir

        #TODO: veryfy if the new position excede the walls boundary
        #.....
        if walls:
            for w in walls:
                pass



#======================================================================================================
    

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
        bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, 3.5), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object
        room_edges[3 if room_orient[1]==True else 1].select = True
        bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit
        bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "mirror":False}, TRANSFORM_OT_translate={"value":(0, 0, 3.5), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.select_all(action='DESELECT')

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object

        room_me.polygons[1].select = True
        room_me.polygons[2].select = True

        bpy.ops.object.mode_set(mode='EDIT', toggle=False) #edit

        bpy.ops.object.material_slot_assign()

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False) #object


        # New Version 
        # ================================================================
        print ('\nSearching for floating objects...')

        walls = [Vector((greatest_x, 0, 0)), Vector((0, greatest_y, 0))]
    
        non_floating_obj_category = ("Camera","Light","bed","chair","dining table","toilet","shelf","bedside table","refrigerator","grass","blade","room","blanket","smoke")
        onWall_obj_category = ("tv", "shelf")
        support_obj_category = ("bed", "chair", "dining table", "grass", "ground", "bedside table")

        fornitures = []

        # Wrapping each objects in a forniture class which contains useful information
        # in order to easly position them in the scene
        for obj in bpy.context.scene.objects:
            if not obj.name.startswith(non_floating_obj_category):
                fornitures.append(
                    Forniture(obj,
                            ground_z,
                            onWall=obj.name.startswith(onWall_obj_category), 
                            floating= not obj.name.startswith(non_floating_obj_category),
                            )
                )

        # Creo tavolini e mensole sotto gli oggetti a mezz'aria, se non già presenti
        print ('\nSearching for floating objects...')
        for obj in fornitures:
            if obj.isFloating:
                if obj.high == "m":
                    support = "dining table"
                    print (str(obj.objRef.name)+' will need a dining table/bedside table')

                elif obj.high == "h":
                    support = "shelf" 
                    print (str(obj.objRef.name)+' will need a shelf')
                else:
                    support = "ground"
                    print (str(obj.objRef.name)+' is close to the ground')

                putSupport(support, fornitures, ground_z, walls, obj, database_path, occurrencies)  # FUTURE VERSIONS: LIST OF OBJECT WHICH CAN BE USED AS SUPPORT
        
        # ================================================================

        for obj in bpy.data.objects:
            obj.lock_location=(False, False, False)
            obj.lock_rotation=(True, True, True)

        return {'FINISHED'}


def putSupport(type: str, fornitures: list, ground_z, walls: list, forniture: Forniture, database_path, occurrencies):
    """
    Take the obj and try to put it on a object avoiding collision between objects
    If an object to be putted on a shelf has collisions
    search for nearest object which have a support attribute.
    If not put a support avoiding collision
    """
    # For non support objects find a support and if he have free space available
    # put the forniture above that support
    if not isinstance(forniture, Support):

        # Update the near objects list
        forniture.near_object_list(fornitures)

        for obj in [f for f in forniture.interaction_objects if isinstance(f['fornitureRef'], Support)]:
            support = obj["fornitureRef"]
            if support.isFree():
                
                support.putObjectAbove(forniture)
                # Put the forniture ABOVE the support
                forniture.objRef.location.z += (support.objRef.dimensions.z + forniture.objRef.dimensions.z) * 0.5

                return

    # Deselecting and importing the new support mesh from the database
    bpy.ops.object.select_all(action='DESELECT')

    if type == "shelf":
        onWall = True
        floating = False

        bpy.ops.wm.append(
                        directory=database_path,
                        filename="entire_collection.blend\\Object\\" + type,
                        )

    elif type == "dining table":
        onWall = False
        floating = False

        bpy.ops.wm.append(
                        directory=database_path,
                        filename="entire_collection.blend\\Object\\" + type,
                        )
        
        
    elif type=="ground":
        print("Putted on the ground")
        forniture.isFloating=False
        return

    else:
        print("TBI supporter = createOther()")
        return


    # Retrieve object Reference
    if type in occurrencies.keys():
        occurrencies[type] += 1
    else:
        occurrencies[type] = 0

    bpy.context.view_layer.objects.active = bpy.data.objects[type]
    ref = bpy.context.object
    ref.name = f"{type}"+ ".%03d" % (occurrencies[type])

    
    # Wrapping the new support in a Support class
    newSupport = Support( ref, ground_z, onWall, floating)
    
    # Put on the wall only if the support need to be attached to the wall
    if newSupport.onWall:
        # TODO: Generalize walls positioning for every walls in the space. SEE nearest_wall_location() in Forniture Class.
        if abs(forniture.objRef.location.x - walls[0].x) < abs(forniture.objRef.location.y - walls[1].y):
            
            bpy.ops.transform.translate(value=(walls[0].x - newSupport.objRef.dimensions.x * 0.5,
                                                forniture.objRef.location.y, 
                                                forniture.objRef.location.z
                                            )
                                        )
            newSupport.setWall('x')

        else:
            bpy.ops.transform.rotate(value=radians(-90), constraint_axis=(False, False, True))

            bpy.ops.transform.translate(value=(forniture.objRef.location.x, 
                                                walls[1].y - newSupport.objRef.dimensions.x * 0.5, 
                                                forniture.objRef.location.z
                                            )
                                        )
            newSupport.setWall('y')
    
    else:
        newSupport.objRef.location = forniture.objRef.location

    
    newSupport.putObjectAbove(forniture)
    # Put the support UNDER the forniture
    newSupport.objRef.location.z -= (newSupport.objRef.dimensions.z + forniture.objRef.dimensions.z) * 0.5

    # TODO: TRY WITH PARENTING
    #...

    # Computing the collision between support and other objects except objects above it after the support positioning
    newSupport.solveCollision(fornitures)
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