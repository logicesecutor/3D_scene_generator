import bpy


def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))


def camera_view_bounds_2d(scene, cam_ob, me_ob):
    """
    Returns camera space bounding box of mesh object.

    Negative 'z' value means the point is behind the camera.

    Takes shift-x/y, lens angle and sensor size into account
    as well as perspective/ortho projections.

    :arg scene: Scene to use for frame size.
    :type scene: :class:`bpy.types.Scene`
    :arg cam_ob: Camera object.
    :type cam_ob: :class:`bpy.types.Object`
    :arg me_ob: Untransformed Mesh.
    :type me_ob: :class:`bpy.types.Mesh´
    :return: a Box object (call its to_tuple() method to get x, y, width and height)
    :rtype: :class:`Box`
    """

    mat = cam_ob.matrix_world.normalized().inverted()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = me_ob.evaluated_get(depsgraph)
    me = mesh_eval.to_mesh()
    me.transform(me_ob.matrix_world)
    me.transform(mat)

    camera = cam_ob.data
    frame = [-v for v in camera.view_frame(scene=scene)[:3]]
    camera_persp = camera.type != 'ORTHO'

    lx = []
    ly = []

    for v in me.vertices:
        co_local = v.co
        z = -co_local.z

        if camera_persp:
            if z == 0.0:
                lx.append(0.5)
                ly.append(0.5)
            # Does it make any sense to drop these?
            #if z <= 0.0:
            #    continue
            else:
                frame = [(v / (v.z / z)) for v in frame]

        min_x, max_x = frame[1].x, frame[2].x
        min_y, max_y = frame[0].y, frame[1].y

        x = (co_local.x - min_x) / (max_x - min_x)
        y = (co_local.y - min_y) / (max_y - min_y)

        lx.append(x)
        ly.append(y)

    min_x = clamp(min(lx), 0.0, 1.0)
    max_x = clamp(max(lx), 0.0, 1.0)
    min_y = clamp(min(ly), 0.0, 1.0)
    max_y = clamp(max(ly), 0.0, 1.0)

    mesh_eval.to_mesh_clear()

    r = scene.render
    fac = r.resolution_percentage * 0.01
    dim_x = r.resolution_x * fac
    dim_y = r.resolution_y * fac

    # Sanity check
    if round((max_x - min_x) * dim_x) == 0 or round((max_y - min_y) * dim_y) == 0:
        return (0, 0, 0, 0)

    return {
        "X": round(min_x * dim_x),  # X
        "Y": round(dim_y - max_y * dim_y),  # Y
        "Width": round((max_x - min_x) * dim_x),  # Width
        "Height": round((max_y - min_y) * dim_y)  # Height
    }


def main(context):

    for me in context.scene.objects:
        if me.type == 'MESH':
            bb_info = camera_view_bounds_2d(context.scene, context.scene.camera, me)

            lh_x = bb_info["X"]
            lh_y = bb_info["Y"]

            rh_x = bb_info["X"] + bb_info["Width"]
            rh_y = bb_info["Y"]

            ll_x = bb_info["X"]
            ll_y = bb_info["Y"] + bb_info["Height"]

            rl_x = bb_info["X"] + bb_info["Width"]
            rl_y = bb_info["Y"] + bb_info["Height"]

            print("Mesh vertices\n")
            print(f"({lh_x},{lh_y}),({rh_x},{rh_y}),({ll_x},{ll_y}),({rl_x},{rl_y})\n")
            
            bpy.ops.render.render(use_viewport=True)
            bpy.ops.render.render()
            bpy.data.images['Render Result'].save_render(filepath="H:\\Blender scripts\\Utils\\render.jpg")


main(bpy.context)
