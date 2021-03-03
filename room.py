import bpy
import bmesh
import os
from mathutils import Matrix


class RoomOperator(bpy.types.Operator):
    bl_idname = "view3d.room"
    bl_label = "room generation"
    bl_description = "Generates a room basing on the position of the objects."

    def execute(self, context):
        ground_z = 0
        bpy.ops.object.select_all(action='DESELECT')

        for obj in bpy.data.objects:
            
            if obj != bpy.data.objects["Camera"] and obj != bpy.data.objects["Light"]:

                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                lowest_z = computeExternVert(obj,2,'MIN','GLOBAL')

                #converto lowest_z in coordinate globali
                #lowest_z = obj.location[2] + lowest_z

                print(obj.name+" lowest vert: "+ str(lowest_z))
                
                if lowest_z < ground_z:
                    ground_z = lowest_z
                    print("new ground_z: " + str(ground_z))

                #tolgo la edit mode e deseleziono l'oggetto
                bpy.ops.object.editmode_toggle()
                obj.select_set(False)

        #importo il pavimento, attento al percorso
        # Getting Current Working Directory
        cwd = os.getcwd()
        database_path = f"{cwd}/Mesh database"  

        bpy.ops.wm.append(
                    directory=database_path,
                    filename="entire_collection.blend\\Object\\floor")

        #porto il pavimento alla z minima
        bpy.ops.transform.translate(value=(0, 0, ground_z))

        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}

def computeExternVert(obj, axis, find, space):
    # edit mode per selezionare vertici
    bpy.ops.object.editmode_toggle()

    #space = 'LOCAL' or 'GLOBAL'
    #find = 'MIN' or 'MAX'
    TOL = 1e-7
    M = obj.matrix_world if space == 'GLOBAL' else Matrix()
    me = obj.data

    bm = bmesh.from_edit_mesh(me)

    if axis==0:
        verts = sorted(bm.verts, key=lambda v: (M @ v.co).x)
    elif axis==0:
        verts = sorted(bm.verts, key=lambda v: (M @ v.co).y)
    else:
        verts = sorted(bm.verts, key=lambda v: (M @ v.co).z)

    bm.select_flush(False)
    #bm.select_flush_mode()

    if axis==0:
        z = (M @ verts[-1 if find == 'MAX' else 0].co).x
    elif axis==0:
        z = (M @ verts[-1 if find == 'MAX' else 0].co).y
    else:
        z = (M @ verts[-1 if find == 'MAX' else 0].co).z
    
    bmesh.update_edit_mesh(me)

    #ritorno il vertice più basso
    return (obj.matrix_world @ verts[0].co)[2]