import bpy
from .blender_utils import optimize_scene

class OptimizeSceneOperator(bpy.types.Operator):
    # Tooltip
    """Optimize Roomle static"""

    bl_idname = "scene.roomle_optimize"
    bl_label = "Optimize Roomle static"

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        optimize_scene()
        return {'FINISHED'}

def register():
    bpy.utils.register_class(OptimizeSceneOperator)


def unregister():
    bpy.utils.unregister_class(OptimizeSceneOperator)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.scene.roomle_optimize()
