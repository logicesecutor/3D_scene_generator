import bpy

import os,io
import logging as log



from math import pi,ceil
import time
from mathutils import Vector

from imageai.Detection import ObjectDetection

class PositioningOperator(bpy.types.Operator):
    bl_idname = "view3d.object_positioning"
    bl_label = "object positioning"
    bl_description = "Automatic object recognition and positioning."
    
    def execute(self,context):

            #Parametri che venivano passati
            RENDER=False
            FROM_SCENE=False
            
            log.basicConfig(filename="LOG.log", filemode="w", level=log.INFO)
            
            # Getting Current Working Directory
            cwd = os.getcwd()
            database_path = f"{cwd}/Mesh database"  
            imagepath=bpy.context.scene['image_filepath']
            # Default location of object spawn
            default_location = Vector((0.0 ,0.0, 0.0))
            
            # Massimo numero di loop per evitare effetto ping-pong degli errori
            MAX_LOOP = 5
            # Massimo errore nella sovrapposizione
            MAX_ERR = 0.03 # 3%
            # Massimo numero di vertici in una mesh
            MAX_N_VERTICES = 3500
            # Lista di appoggio per i dati delle mesh nella scena
            meshes = []
            occurences = {}

            #Utility variables
            scene = context.scene
            camera = context.scene.camera
            
            
            #TODO: PULIRE LA SCENA DA OGNI OGGETTO E METTERE UNA NUOVA CAMERA DI CUI SAPPIAMO
            #      I PARAMETRI E LA MATRICE DI ROTAZIONE
            #      ...
            
            #TODO: CREARE LA CAMERA NELLA POSIZIONE OTTENUTA
            #      ...
            
            
            #TODO: FARE IL REMAPPING DELLA RISOLUZIONE DELL'IMMAGINE DI INPUT IN MODO CHE COMBACI CON LA
            #      RISOLUZIONE IN PIXEL DELLA CAMERA IN MODO DA GENERALIZZARE L'ALGORITMO AD OGNI IMMAGINE DI INPUT
            #      ...
            
            
            # USO LA MATRICE DI TRASFORMAZIONE DELLA CAMERA PER 
            # OTTENERE I VETTORI DEGLI ASSI SUI QUALI SPOSTARE L'OGGETO
            camera_dir = camera.rotation_euler.to_matrix()
            
            # PER SCOPO DI DEBUG 
            if FROM_SCENE:
                for me in context.scene.objects:
                    if me.type == 'MESH':
                        #Tolgo i casi in cui sia un oggetto fuori camera
                        bb_image = bb_from_scene(context, me)
                        if bb_image!= None: 
                            meshes.append(bb_image) 
                        else:
                            continue
                        
            # Analizzo l'immagine di input Con ImageAI
            else:
                start = time.time()
                
                meshes = detect(imagepath)
                log.debug(meshes)

                end = time.time()
                
                print(f"Inference time:: {end-start}")
                
            
            start = time.time()
            
            for bb_image in meshes:
                
                if FROM_SCENE:
                    # INSERISCO UNA NUOVA MESH DAL DATABASE CHE COMBACIA IN UNA LOCATION DI DEFAULT (0, 0, 0)
                    bpy.ops.mesh.primitive_cube_add(location=default_location)
                    mesh_obj = context.object
                    
                else:
                    # CERCO MESH CORRISPONDENTE NEL DATABASE
                    mesh_name = bb_image["name"]+".fbx"
                    if mesh_name in os.listdir(path=database_path):
                        bpy.ops.import_scene.fbx(filepath=database_path+"//"+ mesh_name)
                        # SELEZIONO LA MESH APPENA INSERITA E LA RINOMINO
                        if bb_image["name"] in occurences.keys():
                            occurences[bb_image["name"]] += 1
                        else:
                            occurences[bb_image["name"]] = 0
                        
                        bpy.context.view_layer.objects.active = bpy.data.objects[bb_image["name"]]
                        mesh_obj = context.object
                        mesh_obj.name = f"{bb_image['name']}"+ str(occurences[bb_image["name"]])

                        # APPLICO IL MODIFIER "DECIMATE" PER RIDURRE LA COMPLESSITÁ DELL'ALGORITMO
                        n_vrt = len(mesh_obj.data.vertices.items())
                        ratio = MAX_N_VERTICES / n_vrt
                
                        if n_vrt > MAX_N_VERTICES:
                            # DECIMATE MODIFIER
                            bpy.ops.object.modifier_add(type="DECIMATE")
                            bpy.context.object.modifiers["Decimate"].ratio = ratio
                            bpy.ops.object.modifier_apply()
                            print(f"Applied DECIMATE modifier with ratio of {ratio}")
                    else:
                        bpy.ops.mesh.primitive_cube_add(location=default_location)
                        mesh_obj = context.object
                        
                # allontano di focal_lenght/10 gli oggetti dalla camera
                bpy.ops.transform.translate(value = bpy.context.scene.camera.matrix_world.to_3x3() @ Vector((0,0,-1*bpy.data.cameras["Camera"].lens/10)))
                
                # DEPTH ESTIMATION-DATA PER POSIZIONAMENTO NELLA PROFONDITÁ
                # ...
                # RIUTILIZZO DELA FUNZIONE DEPTH PER SCALARE L'OGGETTO
                
                # APPROSSIMAZIONI SUCCESSIVE(DA OTTIMIZZARE)
                pos_location(context, mesh_obj, bb_image, camera_dir, MAX_ERR)
                camera_depth_dir = mesh_obj.location - camera.location
                
                loop_counter = 0            
                while compute_all_error(context, mesh_obj, bb_image, MAX_ERR) and loop_counter < MAX_LOOP:
                    
                    pos_depth(context, mesh_obj, bb_image, camera_depth_dir, MAX_ERR)
                    pos_rotation(context, mesh_obj, bb_image, MAX_ERR)
                    
                    loop_counter += 1
                
                # CALCOLO LA BOUNDING BOX FINALE (SOLO A SCOPO INFORMATIVO, SI PUÓ ELIMINARE)
                bb_mesh = bb2D(scene, camera, mesh_obj)
                camera_obj_distance = context.object.location - camera.location
                
                log.info(f"Finished with {bb_mesh['name']} -> width::{bb_mesh['Width']}, height::{bb_mesh['Height']}, "
                        f"area::{bb_mesh['Area']}, distance from camera::{camera_obj_distance.magnitude}\n__________________")
        
            end = time.time()
            print(f"Positioning time:: {end-start}")
                            
                            
            if RENDER:
                # RENDER SCENA CREATA             
                bpy.ops.render.render(use_viewport=True)
                bpy.ops.render.render()
                bpy.data.images['Render Result'].save_render(filepath=f"{cwd}/render.jpg")

                log.info(f"Render done and saved in: {cwd}")

            return {'FINISHED'}

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

def bb_from_scene(context, me):
        
    log.info(f"2D bounding box vertices {me.name}:")
    
    bb_image = bb2D(context.scene, context.scene.camera, me)

    #LOGGO I DATI SUL FILE DI LOGGING
    log.info(bb_image)
    log.info("__________________")

    return bb_image
            
def compute_all_error(context, mesh_obj, bb_image, MAX_ERR):
    
    bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
    avg_err = (compute_err(bb_image['X'], bb_mesh['X']) + compute_err(bb_image['Y'], bb_mesh['Y'])) * 0.5
    
    return True if (avg_err > MAX_ERR or compute_err(bb_image['AR'], bb_mesh['AR']) > MAX_ERR or compute_err(bb_image['Area'], bb_mesh['Area']) > MAX_ERR) else False
    
    
def compute_err(ideal_value, computed_value):
    
    return abs(ideal_value - computed_value) / ideal_value



def pos_rotation(context, mesh_obj, bb_image, MAX_ERR):
    
    # POSIZIONAMENTO-----ROTAZIONE
    # ar_  = aspect ratio
    
    # Quanto ruotare in radianti ad ogni passo dell' algoritmo
    rotation_step = 0.01
    
    # CONFRONTO L'ASPECT RATIO DELLE BOUNDING BOX CALCOLANDONE L'ERRORE
    for i in range(ceil(2 * pi / rotation_step)):
        
        bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
        ar_err = compute_err(bb_image['AR'], bb_mesh['AR']) 
        
        if ar_err > MAX_ERR:
            mesh_obj.rotation_euler.z += rotation_step
            
        else: 
            break
    
    # LOG SU FILE
    log.info(f"{mesh_obj.name} rotated -> aspect ratio:: {bb_mesh['AR']}, error of:: {ar_err}")
        
        
def pos_depth(context, mesh_obj, bb_image, camera_rot_vec, MAX_ERR):
    
    # POSIZIONAMENTO-----PROFONDITÁ
    
    # Quanto spostare ad ogni passo dell' algoritmo
    depth_step = 0.01
            
    # TODO: capire quanti cicli servono per ottenere un risultato soddisfacente
    for i in range(ceil(context.scene.render.resolution_y * 0.5)):
        
        # CALCOLO LE AREE DELLE BOUNDING BOX
        bb_mesh = bb2D(context.scene, context.scene.camera, mesh_obj)
        
        delta_area = bb_image["Area"] - bb_mesh["Area"]
        area_err = compute_err(bb_image["Area"], bb_mesh["Area"])
        
        if delta_area < 0 and area_err > MAX_ERR:
            mesh_obj.location += camera_rot_vec * depth_step
            
        elif delta_area > 0 and area_err > MAX_ERR: 
            mesh_obj.location -= camera_rot_vec * depth_step
            
        else:
            break
    
    # LOG SU FILE  
    log.info(f"{mesh_obj.name} depth positioned -> Bounding Box area:: {bb_mesh['Area']}, error of:: {area_err}")
    
    
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
        

def detect(imagepath):
    cwd = os.getcwd()

    meshes = []

    detector = ObjectDetection()
    detector.setModelTypeAsRetinaNet()
    detector.setModelPath(f"{cwd}/Image Ai/retinanet.h5")
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

            print(f"{name} : {probability} : {box_points}", file=fout)
            print("--------------------------------", file=fout)
    
    return meshes
            

