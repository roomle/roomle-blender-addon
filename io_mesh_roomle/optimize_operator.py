# -----------------------------------------------------------------------
# 
#  Copyright 2019 Roomle GmbH. All Rights Reserved.
# 
#  This Software is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
# 
#  NOTICE: All information contained herein is, and remains
#  the property of Roomle. The intellectual and technical concepts contained
#  herein are proprietary to Roomle and are protected by copyright law.
#  Dissemination of this information or reproduction of this material
#  is strictly forbidden unless prior written permission is obtained
#  from Roomle.
# -----------------------------------------------------------------------

import bpy

from bpy.props import BoolProperty

from .blender_utils import optimize_scene

class OptimizeSceneOperator(bpy.types.Operator):
    # Tooltip
    """Optimize Roomle static"""

    bl_idname = "scene.roomle_optimize"
    bl_label = "Optimize Roomle static"
    bl_options = {'REGISTER', 'UNDO'} # 'PRESET'

    center_scene = BoolProperty(name="Center Scene", description="center scene horicontally and place it on x-y plane vertically.", default=True)
    reset_transforms = BoolProperty(name="Reset Transforms", description="Remove hierarchy, apply scale/rotation/translation", default=True)

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode=='OBJECT'

    def execute(self, context):
        optimize_scene(center_scene=self.center_scene, reset_transforms=self.reset_transforms)
        self.report({'INFO'},'Optimized!')
        return {'FINISHED'}

def register():
    bpy.utils.register_class(OptimizeSceneOperator)


def unregister():
    bpy.utils.unregister_class(OptimizeSceneOperator)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.scene.roomle_optimize()
