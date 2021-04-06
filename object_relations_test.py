import bpy
import random

# SCENE OBJECTS WRAPPER CLASS
class Forniture():

    MEDIUM_threshold = 0.7
    HIGH_Threshold = 1.5

    def __init__(self, obj, objects, onWall, floating, support):

        self.objRef = obj

        self.onWall = onWall
        self.isFloating = floating
        self.support = support
        self.high = self.defineObjHigh()
        self.near_objects = []
        self.nearest_wall = []

        if not self.support:
            self.objAbove = []


    def update(self, objects, walls, overlapping_radius):

        self.near_objects = self.nearest_object_list(objects, overlapping_radius)
        self.nearest_wall = self.nearest_wall_location(walls)
        

    def nearest_object_list(self, objects, overlapping_radius):
        nearest=[]
        for obj in objects:
            if obj != target_obj:
                if (obj.location - target_obj.location).magnitude < overlapping_radius:
                    nearest.append(obj)

        return nearest


    def collide(self):

        return True if self.near_objects != [] else False


    def nearest_wall_location(self, walls):

        nearest_wall = float('inf')

        for wall in walls:
            dist = (wall.location - self.objRef.location).magnitude
            if dist < nearest_wall:
                nearest_wall = dist
                save_wall = wall

        return save_wall


    def defineObjHigh(self):

        if self.objRef.location.z > self.HIGH_Threshold:
            return "h"
        elif self.objRef.location.z > self.MEDIUM_threshold:
            return "m"
        else:
            return "l"



walls = []
floating_obj_category = ("Camera","Light","bed","chair","dining table","toilet","shelf","bedside table","refrigerator","grass","blade","room","blanket","smoke")
onWall_obj_category = ("television", "shelf")
support_obj_category = ("bed", "chair", "dining table", "grass", "ground", "bedside table")
fornitures = []

# Parsing all the objects and wrapp all of them in a Forniture Object
for obj in bpy.context.scene.objects:
    fornitures.append( Forniture(obj,
                                onWall=obj.name.startswith(onWall_obj_category), 
                                isFloating=obj.name.startswith(floating_obj_category), 
                                support=obj.name.startswith(support_obj_category),
                                )
                    )

# Chose the action on each object
for forniture in fornitures:
    if forniture.isFloating and not forniture.onWall:
        if forniture.high == "l":
            putForniture(table, forniture)

        elif forniture.high == "m" :
            #Choose a random forniture from a list of elegible objects
            randomForniture = random.choices([f for f in fornitures if f.support])
            putForniture(randomForniture, forniture)

        else:
            putForniture(shelf, forniture)

    elif forniture.isFloating and forniture.onWall:
        putForniture(wall, forniture)



def putForniture(support, forniture):

    # Match the wall rotation
    forniture.objRef.location = forniture.nearest_wall.location
