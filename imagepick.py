import bpy
import struct
 
class ImagePick(bpy.types.Operator):
    bl_idname = "view3d.imagepick"
    bl_label = "Import"
 
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
 
    my_float = bpy.props.FloatProperty(name="Float")
    my_bool = bpy.props.BoolProperty(name="Toggle Option")
    my_string = bpy.props.StringProperty(name="String Value")
 
    def execute(self, context):
        bpy.context.scene['image_filepath'] = self.filepath   #store the path for later use
        print('path: ' + bpy.context.scene['image_filepath'])
        return {'FINISHED'}
 
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
 
    # def draw(self, context):
    #     layout = self.layout
    #     col = layout.column()
    #     col.label(text="Custom Interface!")
 
    #     row = col.row()
    #     row.prop(self, "my_float")
    #     row.prop(self, "my_bool")
 
    #     col.prop(self, "my_string")
 