import bpy

class Test_PT_Panel(bpy.types.Panel):
    bl_idname = "Test_PT_Panel"
    bl_label = "3D Scene Generator"
    bl_category = "3D Scene Generator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI" 

    def draw(self,context):
        layout = self.layout

        row = layout.row()
        row.operator("view3d.imagepick", icon = 'FILE_IMAGE')
        
        layout.separator()

        row = layout.row()
        row.operator("view3d.vp_detection", text = "Calibrate Camera", icon = 'ORIENTATION_GLOBAL')
        
        layout.separator()

        row = layout.row()
        row.operator("view3d.object_positioning", text = "Object Positioning", icon = 'SNAP_VOLUME')
        
        layout.separator()

        row = layout.row()
        row.operator("view3d.room", text = "Generate room", icon = 'AXIS_TOP')
        
        layout.separator()

        row = layout.row()
        row.operator("render.render", text = "Render", icon = 'IMAGE_BACKGROUND')
        
        row = layout.row()
        