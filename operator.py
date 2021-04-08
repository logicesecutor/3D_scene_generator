import bpy
import mathutils

from . import reference

def get_or_create_camera():
    cam_obj = bpy.context.scene.camera
    if not cam_obj:
        bpy.ops.object.camera_add()
        cam_obj = bpy.context.object
    cam = bpy.data.cameras[cam_obj.data.name]
    return (cam_obj, cam)

from math import sqrt, pi, degrees

from . import polynomial
from . import rootfinder
from . import algebra
from . import cameraplane
from . import transformation
from . import reference
from . import solverectangle
from . import scene
from . import threepoint

### Operator FXY PR VV ############################################################

class CameraCalibration_FXY_PR_VV_Operator(bpy.types.Operator):
    """Calibrates the focal length, lens shift (horizontal and vertical), position and rotation of the active camera."""
    bl_idname = "camera.camera_calibration_fxy_pr_vv"
    bl_label = "Solve Focal+X+Y"
    bl_options = {"REGISTER", "UNDO"}

    # Properties
    vertical_property : bpy.props.BoolProperty(name = "Vertical orientation", description = "Places the reconstructed rectangle in vertical orientation", default = False)
    size_property : bpy.props.FloatProperty(name="Size", description = "Size of the reconstructed rectangle", default = 1.0, min = 0.0, soft_min = 0.0, unit = "LENGTH")

    #@classmethod
    #def poll(cls, context):
    #    return context.active_object is not None and context.space_data.type == "PROPERTIES"

    def execute(self, context):
        # Get the camere of the scene
        scn = context.scene
        # Get the currently selected object
        obj = bpy.context.active_object
        # Check whether it is a mesh with 6 vertices, 1 polygon, with 4 vertices and 2 dangling vertices
        if not obj.data.name in bpy.data.meshes or not len(obj.data.vertices) == 6 or not len(obj.data.polygons) == 1 or not len(obj.data.polygons[0].vertices) == 4 or not len(obj.data.edges) == 6:
            self.report({'ERROR'}, "Selected object must be a mesh with one polygon of 4 vertices with two dangling vertices.")
            return {'CANCELLED'}
        # Get the edges that are not part of the polygon
        print("Polygon edges:", obj.data.polygons[0].edge_keys)
        dangling_edges = []
        for edge in obj.data.edges:
            if not edge.key in obj.data.polygons[0].edge_keys:
                dangling_edges.append(edge)
        print("Dangling edges:", dangling_edges[0].key, dangling_edges[1].key)
        # Get the indices of the attached and dangling vertices
        dangling_vertices = [0, 0]
        attached_vertices = [0, 0]
        for i in range(2):
            if dangling_edges[i].key[0] in obj.data.polygons[0].vertices:
                dangling_vertices[i] = dangling_edges[i].key[1]
                attached_vertices[i] = dangling_edges[i].key[0]
            else:
                dangling_vertices[i] = dangling_edges[i].key[0]
                attached_vertices[i] = dangling_edges[i].key[1]
        print("Dangling vertices:", dangling_vertices)
        print("Attached vertices:", attached_vertices)
        # Convert indices to vertices
        for i in range(2):
            dangling_vertices[i] = transformation.vertex_apply_transformation(obj.data.vertices[dangling_vertices[i]].co, obj.scale, obj.rotation_euler, obj.location).to_2d()
            attached_vertices[i] = transformation.vertex_apply_transformation(obj.data.vertices[attached_vertices[i]].co, obj.scale, obj.rotation_euler, obj.location).to_2d()
        # Get the vertex coordinates and apply the transformation to get global coordinates, then project to 2d
        vertices = []
        for i in range(4):
            index = obj.data.polygons[0].vertices[i]
            vertices.append(transformation.vertex_apply_transformation(obj.data.vertices[index].co, obj.scale, obj.rotation_euler, obj.location).to_2d())
        # Check whether the polygon is convex (this also checks for degnerate polygons)
        if not cameraplane.is_convex(vertices[0], vertices[1], vertices[2], vertices[3]):
            self.report({'ERROR'}, "The polygon in the mesh must be convex and may not be degenerate.")
            return {'CANCELLED'}
        # Check for parallel edges
        if cameraplane.is_collinear(vertices[0] - vertices[1], vertices[3] - vertices[2]) or cameraplane.is_collinear(vertices[0] - vertices[3], vertices[1] - vertices[2]) or cameraplane.is_collinear(dangling_vertices[0] - attached_vertices[0], dangling_vertices[1] - attached_vertices[1]):
            self.report({'ERROR'}, "Edges must not be parallel.")
            return {'CANCELLED'}

        # Get the properties
        #props = bpy.context.scene.camera_calibration_pvr_properties
        # Reference image
        image_obj = bpy.data.objects["Empty"]
        if not image_obj:
            self.report({'ERROR'}, "Set a reference image.")
            return {'CANCELLED'}
        image, w, h, scale, offx, offy = reference.get_reference_image_data(image_obj)
        # Scale is the horizontal dimension. If in portrait mode, use the vertical dimension.
        if h > w:
            scale = scale / w * h

        # Perform the actual calibration
        calibration_data = threepoint.calibrate_camera_shifted(vertices, attached_vertices, dangling_vertices, scale)
        cam_focal, cam_pos, cam_rot, coords, rec_size, camera_shift_x, camera_shift_y = calibration_data

        if self.size_property > 0:
            size_factor = self.size_property / rec_size
        else:
            size_factor = 1.0 / rec_size
        cam_obj, cam = scene.get_or_create_camera(scn)
        # Set intrinsic camera parameters
        scene.set_camera_parameters(cam, lens = cam_focal, shift_x = camera_shift_x, shift_y = camera_shift_y)
        # Set extrinsic camera parameters and add a new rectangle
        scene.update_scene(cam_obj, cam_pos, cam_rot, self.vertical_property, scn, w, h, obj.name, coords, size_factor)
        # Set background image
        reference.camera_apply_reference_image(cam, image)

        # Switch to the active camera
        area = bpy.context.area.type
        bpy.context.area.type = "VIEW_3D"
        bpy.ops.view3d.view_camera()
        bpy.context.area.type = area

        return {'FINISHED'}