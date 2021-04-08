# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "Create_rectangle",
    "author" : "Lorenzo Semeraro",
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