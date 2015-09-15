import bpy

from bpy.props import (
        StringProperty,
        BoolProperty,
        CollectionProperty,
        EnumProperty,
        FloatProperty,
        )
from bpy_extras.io_utils import (
    ExportHelper,
    orientation_helper_factory,
    axis_conversion
    )
from bpy.types import (
    Operator
    )

RoomleOrientationHelper = orientation_helper_factory("RoomleOrientationHelper", axis_forward='Y', axis_up='Z')

class ExportRoomleScript(Operator, ExportHelper, RoomleOrientationHelper):
    """Save a Roomle Script from the active object"""
    bl_idname = "export_mesh.roomle_script"
    bl_label = "Export Roomle Script"
    
    filename_ext = ".txt"
    filter_glob = StringProperty(default="*.txt", options={'HIDDEN'})
    
    global_scale = FloatProperty(
            name="Scale",
            min=0.01, max=1000000.0,
            default=1000.0,
            )

    use_scene_unit = BoolProperty(
            name="Scene Unit",
            description="Apply current scene's unit (as defined by unit scale) to exported data",
            default=False,
            )
            
    use_mesh_modifiers = BoolProperty(
            name="Apply Modifiers",
            description="Apply the modifiers before saving",
            default=True,
            )
            
    def execute(self, context):
        from mathutils import Matrix, Vector
        from . import baconx
        
        global_matrix = axis_conversion(to_forward='-Y',to_up='Z',).to_4x4() * Matrix.Scale(global_scale, 4) * Matrix.Scale(-1,4,Vector((1,0,0)))

        command = baconx.create_object_commands(bpy.context.active_object, global_matrix)
        command = '{"id":"catalogExtId:component1","geometry":"'+command+'"}'

        write_roomle_script(object=bpy.context.active_object, global_matrix=global_matrix, **keywords);

        return {'FINISHED'}

def menu_export(self, context):
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".txt"
    self.layout.operator(ExportRoomleScript.bl_idname, text="Roomle Script (.txt)")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_export)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_export)

if __name__ == "__main__":
    register()
    