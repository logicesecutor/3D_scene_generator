bl_info = {
    "name" : "3D_scene_generator",
    "author" : "Semeraro Lorenzo, Bardella Christian",
    "description" : "",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "View3D",
    "warning" : "",
    "category" : "Generic"  
}

import bpy 

from . vp_detection import VPDetectionOperator
from . positioning import PositioningOperator
from . room import RoomOperator
from . panel        import Test_PT_Panel
from . operator     import CameraCalibration_FXY_PR_VV_Operator
from . imagepick    import ImagePick
from . import operator
from . import properties
from . import polynomial
from . import rootfinder
from . import algebra
from . import cameraplane
from . import transformation
from . import scene
from . import solverectangle
from . import threepoint

### To separate the errors in console ###########################################

print('---------------------------------')

classes = (ImagePick, VPDetectionOperator, PositioningOperator, RoomOperator, Test_PT_Panel, CameraCalibration_FXY_PR_VV_Operator)
register, unregister = bpy.utils.register_classes_factory(classes)