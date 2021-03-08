import bpy
import time

class GravityOperator(bpy.types.Operator):
    bl_idname = "view3d.gravity"
    bl_label = "gravity activation"
    bl_description = "Allows objects with Rigid Body to fall down."
    
    def execute(self, context):

        # Lock sulle rotazioni per tutti gli assi, e lock sulle traslazioni su x e y 
        # (in questo modo l'oggetto non può far altro che cadere in basso e il positioning non verrà intaccato)
        for obj in bpy.data.objects:
            obj.lock_location=(False, False, False)
            obj.lock_rotation=(True, True, True)

        bpy.context.scene.frame_set(0)
        bpy.ops.screen.animation_play()
        time.sleep(0.5)
        bpy.ops.screen.animation_play()
        
        #calcolo il frame 50, ipotizzando che tutto sia caduto sulle superfici sottostanti
        bpy.context.scene.frame_end = 50
        bpy.ops.screen.frame_jump(end=True)
        return {'FINISHED'}
