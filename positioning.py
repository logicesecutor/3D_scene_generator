import bpy
import bmesh

import os,io
import time

from math import pi,ceil, floor, radians, pow, sqrt
from mathutils import Vector, Matrix
import numpy as np
from matplotlib import pyplot as plt
from PIL import Image
import numpy as np

from .depth_prediction import deptPredictionThread

from threading import Thread

from imageai.Detection import ObjectDetection

class PositioningOperator(bpy.types.Operator):
    bl_idname = "view3d.object_positioning"
    bl_label = "object positioning"
    bl_description = "Automatic object recognition and positioning."
    
    def execute(self, context):

        print('\n---------------  POSITIONING  ---------------')

        # Set True to render the scene
        RENDER=False
    
        # Getting Current Working Directory
        cwd = os.getcwd()
        database_path = f"{cwd}/Mesh database"  
        imagepath = bpy.context.scene['image_filepath']
        # Default location of object spawn
        default_location = Vector((0.0 ,0.0, 0.0))  # Center of the world
        # Thread object for depth prediction
        depth_pred_thread = deptPredictionThread(cwd, imagepath)
        depth_pred_thread.start()
        # Max aspect ratio error
        MAX_ERR = 0.75 #75%
        # Max vertices in a mesh before apply decimate modifier
        MAX_N_VERTICES = 5000
        # List to store all meshes BB data
        meshes = []
        occurences = {}
        # Camera direction vectors
        camera_dir = camera_dir_mat()

        #Useful variables
        scene = context.scene
        camera = context.scene.camera
        
        
        #CLEAR THE SCENE EXCEPT THE CAMERA, OBV
        for o in bpy.context.scene.objects:
            if o.type == 'MESH':
                o.select_set(True)
            else:
                o.select_set(False)

        # Call the operator only once
        bpy.ops.object.delete()
        
        

        # IMAGE-AI OBJECT DETECTION
        inference_start = time.time()
        meshes = detect(imagepath)
        
        print(f"Inference time:: {time.time()-inference_start}\n")

        depth_pred_thread.join()
        #Loading depth data from pickled numpy ndarray: shape(1, 128, 160, 1)
        pred_array = np.load("depth_prediction.dat", allow_pickle=True)
            
        
        # POSITIONING EVERY OBJECTS IN THE SCENE ACCORDINGLY TO THE IMAGE
        obj_positioning_start = time.time()
        
        for bb_image in meshes:
            
            # SEARCH FOR A MESH IN THE DATABASE WITH THE SAME LABEL
            # AND GIVE IT A PROPER BLENDER LIKE NAME
            mesh_name = bb_image["name"]
            
            with bpy.data.libraries.load(database_path+"\\entire_collection.blend") as (data_from, data_to):
                names = [name for name in data_from.collections]

            if mesh_name in names:
                bpy.ops.wm.append(
                directory=database_path,
                filename="entire_collection.blend\\Collection\\"+bb_image["name"])

                # SELECT THE INSERTED MESH
                if bb_image["name"] in occurences.keys():
                    occurences[bb_image["name"]] += 1
                else:
                    occurences[bb_image["name"]] = 0
                
                bpy.context.view_layer.objects.active = bpy.data.objects[bb_image["name"]]
                mesh_obj = context.object
                mesh_obj.name = f"{bb_image['name']}"+ ".%03d" % (occurences[bb_image["name"]])

                print('\n---------------  '+mesh_obj.name+'  ---------------')
                
                # NUMBER OF VERTICES IN A MESH
                n_vrt = len(mesh_obj.data.vertices.items())
                
                if n_vrt > MAX_N_VERTICES:
                    # APPLY A DECIMATE MODIFIER TO SHRINK DOWN THE COMPLEXITY OF THE MESH
                    ratio = MAX_N_VERTICES/n_vrt
                    
                    bpy.ops.object.modifier_add(type="DECIMATE")
                    bpy.context.object.modifiers["Decimate"].ratio = ratio
                    bpy.ops.object.modifier_apply()
                    
                    print(f"Applied DECIMATE modifier with ratio of {ratio}")
            else:
                bpy.ops.wm.append(
                directory=database_path,
                filename="entire_collection.blend\\Object\\empty box")
                mesh_obj = context.object
                print('\n---------------  ' + bb_image["name"] + '  ---------------')
                print('No ' + bb_image["name"] + ' meshes in db. Replaced it with an empty box.')
            
            #=================================================================================================
            # OBJECT POSITIONING IN CAMERA VIEW
            # TODO: FIND A WAY TO UNDERSTAND IF THE OBJECT IS IN A PROPRIATE
            #       SCALE TO FIT THE CAMERA VIEW
            mesh_obj.location += camera_dir[2] * 10 # meters
            camera_obj_origin_dist = (mesh_obj.location - camera.location).magnitude
 
            try: 
                
                bb_mesh = bb2D(scene, camera, mesh_obj)  #va fatto ora perchè gli oggetti sono nel frustum 

                pos_location_oneshot(context, mesh_obj, bb_image, camera_dir)
                
                camera_obj_dir = (mesh_obj.location - camera.location).normalized()
                
                pos_depth_AI(context, mesh_obj, camera_obj_dir, camera_obj_origin_dist, pred_array)
                
            
            except TypeError:

                print(f"Object {mesh_obj.name} out of camera view. Can't compute Bounding Box.\n"
                    "Next Item.")
                continue
                
            pos_rotation(context, camera, mesh_obj, bb_mesh, bb_image, MAX_ERR)
        
            #==================================================================================================

        print(f"Positioning time:: {time.time()-obj_positioning_start}")
                        
                        
        if RENDER:
            # RENDER CREATED SCENE             
            bpy.ops.render.render(use_viewport=True)
            bpy.ops.render.render()
            bpy.data.images['Render Result'].save_render(filepath=f"{cwd}/render.jpg")

            log.info(f"Render done and saved in: {cwd}")

        generate_grass()

        return {'FINISHED'}


def correction_factor(axis_mat, vector):
    
    #==============================
    # Angle on ZX camera plane
    v = vector.normalized()
    v.y = axis_mat[2].y
    costeta = axis_mat[2].dot(v)
    
    
    # Angle on YZ camera plane
    v = vector.normalized()
    v.x = axis_mat[2].x
    cosalfa = axis_mat[2].dot(v)
    
    return sqrt(pow(cosalfa, 2) + pow(costeta, 2) / (cosalfa * costeta))


def camera_dir_mat():

    camera = bpy.context.scene.camera
    
    right = Vector((1.0, 0.0, 0.0))
    up = Vector((0.0, 1.0, 0.0))
    front = Vector((0.0, 0.0, -1.0))
    
    camera_dir = Matrix((right,up,front))
    camera_dir = camera.rotation_euler.to_matrix() @ camera_dir
    camera_dir.transpose()
    
    return camera_dir


def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))


def bb2D(scene, cam_ob, me_ob):
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
    name = me_ob.name
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

    x = round(min_x * dim_x)
    y = round(dim_y - max_y * dim_y)
    width = round((max_x - min_x) * dim_x)
    height = round((max_y - min_y) * dim_y)
    

    # Sanity check
    if width == 0 or height == 0:
        return None

    return {
        "name": name,
        "X": x+width*0.5,
        "Y": y+height*0.5,
        "Width": width,  
        "Height": height, 
        "AR":  width / height,
        "Area": width * height
    }

    
def compute_err(ideal_value, computed_value):
    
    return abs(ideal_value - computed_value) / ideal_value


def pos_rotation(context, camera, mesh_obj, bb_mesh, bb_image, MAX_ERR):

    # POSITIONING -----> ROTATION
    # ar_  = aspect ratio
    
    #bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
    ar_err = compute_err(bb_image['AR'], bb_mesh['AR'])
    print('Aspect ratio in the image: ' + str(bb_image['AR']))
    print('Aspect ratio of mesh: ' + str(bb_mesh['AR']))
    print('Aspect ratio error: ' + str(ar_err))
    if ar_err > MAX_ERR:
        if (np.linalg.inv(camera.matrix_world) @ mesh_obj.matrix_world)[0][3] > 0:
            mesh_obj.rotation_euler.z -= radians(90)
            print("Error is greater than threshold ("+str(MAX_ERR)+"). " + f"{mesh_obj.name} rotated of -90")
        else:
            mesh_obj.rotation_euler.z += radians(90)
            print("Error is greater than threshold ("+str(MAX_ERR)+"). " + f"{mesh_obj.name} rotated of +90")
        
        

    '''
    OLD METHOD (ITERATIVE)
    # Compare the aspect ratio of the image BB and mesh BB
    for i in range(ceil(2 * pi / rotation_step)):
        
        bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
        ar_err = compute_err(bb_image['AR'], bb_mesh['AR']) 
        
        if ar_err > MAX_ERR:
            mesh_obj.rotation_euler.z += rotation_step
            
        else: 
            break
    '''
        
        
def pos_depth(context, mesh_obj, bb_image, camera_rot_vec, MAX_ERR):
    """ DEPRECATED """
    
    # POSIZIONAMENTO -----> DEPTH
    
    # Meter step for each rotation
    depth_step = 0.02
            
    # TODO: understand how many cycles are needed to obtain a good result
    for i in range(ceil(context.scene.render.resolution_y * 0.5)):
        
        # COMPUTE BB AREAS
        bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
        
        delta_area = bb_image["Area"] - bb_mesh["Area"]
        area_err = compute_err(bb_image["Area"], bb_mesh["Area"])
        
        if delta_area < 0 and area_err > MAX_ERR:

            mesh_obj.location += camera_rot_vec * depth_step
            
        elif delta_area > 0 and area_err > MAX_ERR: 
            mesh_obj.location -= camera_rot_vec * depth_step
      
        else:
            break
    
    print(f"{mesh_obj.name} depth positioned -> Bounding Box area:: {bb_mesh['Area']}, error of:: {area_err}")


def pos_depth_AI(context, mesh_obj, camera_obj_dir, camera_obj_origin_dist, pred, correction_factor=1, mode='avg'):
    
    bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
    
    # Index mapping to correctly acces the numpy array 
    x_old = bb_mesh["X"] - bb_mesh["Width"] * 0.5
    y_old = bb_mesh["Y"] - bb_mesh["Height"] * 0.5
    
    # Scale factor from low to high definition image
    scale_factor_x = len(pred[0,0,:]) / context.scene.render.resolution_x
    scale_factor_y = len(pred[0,:]) / context.scene.render.resolution_y
    
    x_new = floor(scale_factor_x * x_old)
    y_new = floor(scale_factor_y * y_old)
    
    width_new = floor(bb_mesh["Width"] * scale_factor_x)
    height_new = floor(bb_mesh["Height"] * scale_factor_y)
    
    if mode == 'center':
        # Distance vaule from the BB center
        dist = pred[0,y_new+height_new, x_new+width_new,0]
    elif mode == 'avg':
        # Distance value from the average values in the BB area
        dist = np.average(pred[0, y_new : y_new+height_new, x_new : x_new+width_new, 0])
    elif mode == 'w_avg':
        # TODO: DEFINE A WEIGTH MATRIX
        # Distance value from the weigthed average values in the BB area
        dist = np.average(pred[0, y_new : y_new+height_new, x_new : x_new+width_new, 0], weigth= weigth)
    else:
        print("Insert a correct mode: avg or w_avg or center")
        
    
    delta_depth = (dist - camera_obj_origin_dist) * correction_factor
    
    mesh_obj.location += camera_obj_dir * delta_depth
    
    print(f"Predicted distance: {dist}\n"
          f"Initial distance from camera: {camera_obj_origin_dist}\n"
          f"Final distance from camera: {(mesh_obj.location-context.scene.camera.location).magnitude}\n"
          f"Step: {delta_depth}\n"
          f"Corection factor: {correction_factor}(default value=1)\n"
          f"Direction: {camera_obj_dir}")
    
    
def pos_location(context, mesh_obj, bb_image, camera_rot_mat, MAX_ERR):
    
    # POSIZIONAMENTO-----Piano di camera XY
    
    # Quanto spostarsi ad ogni passo dell' algoritmo
    location_step = 0.01
    camera_dir_y = camera_rot_mat[1]
    camera_dir_x = camera_rot_mat[0]
    
    for i in range(ceil(context.scene.render.resolution_y * 0.5)):
        
        bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
        
        delta_Y_location = bb_image["Y"] - bb_mesh["Y"]
        Y_location_err = compute_err(bb_image["Y"], bb_mesh["Y"])
        
        if delta_Y_location < 0 and Y_location_err > MAX_ERR:
            mesh_obj.location -= camera_dir_y * location_step
    
        elif delta_Y_location > 0 and Y_location_err > MAX_ERR:
            mesh_obj.location += camera_dir_y * location_step
            
        else:
            break
        
        
    for i in range(ceil(context.scene.render.resolution_x * 0.5)):
        
        bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
        
        delta_X_location = bb_image["X"] - bb_mesh["X"]
        X_location_err = compute_err(bb_image["X"], bb_mesh["X"])

        if delta_X_location > 0 and X_location_err > MAX_ERR:
            mesh_obj.location += camera_dir_x * location_step
        
        elif delta_X_location < 0 and X_location_err > MAX_ERR:
            mesh_obj.location -= camera_dir_x * location_step
        
        else:
            break                    
        
    # LOG SU FILE  
    log.info(f"{mesh_obj.name} positioned -> center coordinates:: ({bb_mesh['X']}, {bb_mesh['Y']}), X,Y errors:: ({X_location_err}, {Y_location_err})")


def pos_location_oneshot(context, mesh_obj, bb_image, camera_dir):
    
    scene = context.scene
    camera = context.scene.camera

    bb_mesh = bb2D(scene, camera, mesh_obj)

    FL = bpy.data.cameras["Camera"].lens
    CSW =  bpy.data.cameras["Camera"].sensor_width
    CO = (mesh_obj.location - camera.location).magnitude

    dept_scale_fac = (CSW * CO) / FL

    camera_width_pix = scene.render.resolution_x
    camera_height_pix = scene.render.resolution_y

    camera_width_meter = camera.data.view_frame(scene=scene)[0].x * 2
    camera_height_meter = camera.data.view_frame(scene=scene)[0].y * 2

    scale_fac_x = camera_width_meter / camera_width_pix
    scale_fac_y = camera_height_meter / camera_height_pix

    pos_x_meter = (bb_image["X"] - bb_mesh["X"]) * scale_fac_x * dept_scale_fac
    pos_y_meter = (bb_image["Y"] - bb_mesh["Y"]) * scale_fac_y * dept_scale_fac

    print(f"Camera Plane x step: {pos_x_meter}\n"
          f"Camera Plane y step: {pos_y_meter}")

    mesh_obj.location += camera_dir[0] * pos_x_meter
    mesh_obj.location -= camera_dir[1] * pos_y_meter
    

def predict(imagepath):
    
    # import tensorflow.compat.v1 as tf
    # tf.disable_v2_behavior()
    
    cwd = os.getcwd()

    # RELATIVE PATH
    model_data_path = f"{cwd}/trained_model/NYU_FCRN.ckpt"
    image_path = imagepath

    # Default input size
    height = 228
    width = 304
    channels = 3
    batch_size = 1
   
    # Read image
    img = Image.open(image_path)
    img = img.resize([width,height], Image.ANTIALIAS)
    img = np.array(img).astype('float32')
    img = np.expand_dims(np.asarray(img), axis = 0)
   
    # Create a placeholder for the input image
    input_node = tf.placeholder(tf.float32, shape=(None, height, width, channels))

    # Construct the network
    net = models.ResNet50UpProj({'data': input_node}, batch_size, 1, False)
        
    with tf.Session() as sess:

        # Load the converted parameters
        print('Loading the model')

        # Use to load from ckpt file
        saver = tf.train.Saver()     
        saver.restore(sess, model_data_path)

        # Use to load from npy file
        # net.load(model_data_path, sess) 

        # Evalute the network for the given image
        pred = sess.run(net.get_output(), feed_dict={input_node: img})
        plt.imsave(fname=f"{cwd}/output_image.jpg",arr=pred[0,:,:,0])
        
        # # Plot result
        # fig = plt.figure()
        # ii = plt.imshow(pred[0,:,:,0])
        # plt.gray()
        # print(fig.colorbar(ii))
        # plt.show()
        
        return pred[0,:,:,0]


def detect(imagepath):
    cwd = os.getcwd()

    meshes = []

    detector = ObjectDetection()
    # detector.setModelTypeAsRetinaNet()
    # detector.setModelPath(f"{cwd}/Image Ai/retinanet.h5")
    detector.setModelTypeAsYOLOv3()
    detector.setModelPath(f"{cwd}/Image Ai/yolo.h5")
    detector.loadModel()

    detections = detector.detectObjectsFromImage(input_image=imagepath, 
                                                output_image_path=f"{cwd}/image_detect.jpg", 
                                                minimum_percentage_probability=35,
                                                )

    with open('imageDetails.txt',"w") as fout:                               
        for eachObject in detections:

            name = eachObject["name"]
            probability = eachObject["percentage_probability"]
            box_points = eachObject["box_points"]

            width = box_points[2]-box_points[0]
            height = box_points[3]-box_points[1]

            meshes.append({ "name": name,   
                            "X": box_points[0] + width * 0.5,
                            "Y": box_points[1] + height * 0.5,
                            "Width": width,
                            "Height": height, 
                            "AR":  width / height,
                            "Area": width * height
                        })

            print(f"{name} {probability} {box_points}", file=fout)
    
    return meshes

def generate_grass():
    print('----------ROOM GENERATION----------')

    ground_z = 0
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.frame_end = 50

    #Detect the orientation of the room from camera
    camera=bpy.context.scene.camera
    camera_rot=camera.matrix_world.to_3x3() @ Vector((0,0,-1))

    room_orient=[False,False]

    room_orient[0]=False if camera_rot[0]<0 else True
    room_orient[1]=False if camera_rot[1]<0 else True

    print(room_orient)

    for obj in bpy.data.objects:
        
        if obj != bpy.data.objects["Camera"] and obj != bpy.data.objects["Light"]:

            if obj.name=='room' or obj.name=='grass':
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    bpy.ops.object.delete()
            
            obj.lock_location=(False, False, False)
            obj.lock_rotation=(True, True, True)

            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            extern = computeExternVert(obj,'GLOBAL',room_orient)
            lowest_z = extern[2]         
            
            if lowest_z < ground_z:
                ground_z = lowest_z
                #print("new ground_z: " + str(ground_z))

            #tolgo la edit mode e deseleziono l'oggetto
            bpy.ops.object.editmode_toggle()
            obj.select_set(False)

    lowest_z = lowest_z - 0.1

    #importo il pavimento, attento al percorso
    # Getting Current Working Directory
    cwd = os.getcwd()
    database_path = f"{cwd}/Mesh database"  

    bpy.ops.wm.append(
                directory=database_path,
                filename="entire_collection.blend\\Object\\grass")
    
    bpy.data.objects["blade"].hide_viewport=True

    grass_obj=bpy.context.scene.objects["grass"]
    bpy.context.view_layer.objects.active = grass_obj
    #porto il pavimento alla z minima
    bpy.ops.transform.translate(value=(0, 0, ground_z))

    bpy.ops.screen.animation_play()
    
def computeExternVert(obj, space, room_orient):
    # edit mode per selezionare vertici
    bpy.ops.object.editmode_toggle()

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

    x = (M @ verts0[0 if room_orient[0]==False else -1].co).x
    y = (M @ verts1[0 if room_orient[1]==False else -1].co).y
    z = (M @ verts2[0].co).z

    bmesh.update_edit_mesh(me)

    #ritorno i vertici esterni
    return [x,y,z]