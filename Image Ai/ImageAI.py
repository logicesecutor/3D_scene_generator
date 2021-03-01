from imageai.Detection import ObjectDetection
import os,io

cwd = os.getcwd()

detector = ObjectDetection()
detector.setModelTypeAsRetinaNet()
detector.setModelPath(f"{cwd}/retinanet.h5")
detector.loadModel()

detections = detector.detectObjectsFromImage(input_image=f"{cwd}\\interni1.jpg", 
                                             output_image_path=f"{cwd}/roomdetect.jpg", 
                                             minimum_percentage_probability=30,
                                             )

with open('imageDetails.txt',"w") as fout:                               
    for eachObject in detections:

        name = eachObject["name"]
        probability = eachObject["percentage_probability"]
        box_points = eachObject["box_points"]

        print(f"{name} : {probability} : {box_points}", file=fout)
        print("--------------------------------", file=fout)