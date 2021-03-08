import os,io
from .fcrn import ResNet50UpProj 
import numpy as np
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

from threading import Thread
from PIL import Image



class deptPredictionThread(Thread):


    def __init__(self, cwd, imagePath):
        self.cwd = cwd
        self.imagePath = imagePath
        Thread.__init__(self)

    def run(self):
        # RELATIVE PATH
        model_data_path = f"{self.cwd}/trained_model/NYU_FCRN.ckpt"

        # Default input size
        height = 228
        width = 304
        channels = 3
        batch_size = 1

        # Read image
        img = Image.open(self.imagePath)
        img = img.resize([width,height], Image.ANTIALIAS)
        img = np.array(img).astype('float32')
        img = np.expand_dims(np.asarray(img), axis = 0)

        # Create a placeholder for the input image
        input_node = tf.placeholder(tf.float32, shape=(None, height, width, channels))

        # Construct the network
        net = ResNet50UpProj({'data': input_node}, batch_size, 1, False)
            
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

            # Dump the prediction array in a file
            pred.dump(f"{self.cwd}/depth_prediction.dat")

        exit(0)

