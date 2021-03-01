import bpy

def solvefocal(context,image_obj):
    
    import bpy
    import mathutils

    from . import reference
    from math import sqrt, pi, degrees

    from . import polynomial
    from . import rootfinder
    from . import algebra
    from . import cameraplane
    from . import transformation
    from . import solverectangle
    from . import scene
    from . import onepoint
    from . import twopoint
    from . import threepoint

    # Get the camere of the scene
    scn = context.scene
    # Get the currently selected object
    obj = bpy.context.active_object
    # Check whether a mesh with 4 vertices in one polygon is selected
    if not obj.data.name in bpy.data.meshes or not len(obj.data.vertices) == 4 or not len(obj.data.polygons) == 1 or not len(obj.data.polygons[0].vertices) == 4:
        print( "Selected object must be a mesh with 4 vertices in 1 polygon.")
    else:
        # Get the vertex coordinates and transform them to get the global coordinates, then project to 2d
        pa = transformation.vertex_apply_transformation(obj.data.vertices[obj.data.polygons[0].vertices[0]].co, obj.scale, obj.rotation_euler, obj.location).to_2d()
        pb = transformation.vertex_apply_transformation(obj.data.vertices[obj.data.polygons[0].vertices[1]].co, obj.scale, obj.rotation_euler, obj.location).to_2d()
        pc = transformation.vertex_apply_transformation(obj.data.vertices[obj.data.polygons[0].vertices[2]].co, obj.scale, obj.rotation_euler, obj.location).to_2d()
        pd = transformation.vertex_apply_transformation(obj.data.vertices[obj.data.polygons[0].vertices[3]].co, obj.scale, obj.rotation_euler, obj.location).to_2d()
        # Check whether the polygon is convex (this also checks for degnerate polygons)
        if not cameraplane.is_convex(pa, pb, pc, pd):
            print("The polygon in the mesh must be convex and may not be degenerate.")
        else:
            # Check for parallel edges
            if cameraplane.is_trapezoid(pa, pb, pc, pd):
                print("Edges of the input rectangle must not be parallel.")
            else:
                print("Vertices:", pa, pb, pc, pd)

                # Get the properties
                props = bpy.context.scene.camera_calibration_pvr_properties
                # Reference image
                #image_obj = props.image
                if not image_obj:
                    print( "Set a reference image.")
                else:
                    image, w, h, scale, offx, offy = reference.get_reference_image_data(image_obj)
                    # Scale is the horizontal dimension. If in portrait mode, use the vertical dimension.
                    if h > w:
                        scale = scale / w * h

                    # Perform the actual calibration
                    cam_focal, cam_pos, cam_rot, coords, rec_size = threepoint.calibrate_camera(pa, pb, pc, pd, scale)

                    if self.size_property > 0:
                        size_factor = self.size_property / rec_size
                    else:
                        size_factor = 1.0 / rec_size
                    cam_obj, cam = scene.get_or_create_camera(scn)
                    # Set intrinsic camera parameters
                    scene.set_camera_parameters(cam, lens = cam_focal)
                    # Set background image
                    reference.camera_apply_reference_image(cam, image)
                    # Set extrinsic camera parameters and add a new rectangle
                    scene.update_scene(cam_obj, cam_pos, cam_rot, self.vertical_property, scn, w, h, obj.name, coords, size_factor)

                    # Switch to the active camera
                    area = bpy.context.area.type
                    bpy.context.area.type = "VIEW_3D"
                    bpy.ops.view3d.view_camera()
                    bpy.context.area.type = area