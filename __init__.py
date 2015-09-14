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
            min=0.01, max=1000.0,
            default=1.0,
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
        #from . import stl_utils
        #from . import blender_utils
        
#        import itertools
#        from mathutils import Matrix
#        keywords = self.as_keywords(ignore=("axis_forward",
#                                            "axis_up",
#                                            "global_scale",
#                                            "check_existing",
#                                            "filter_glob",
#                                            "use_scene_unit",
#                                            "use_mesh_modifiers",
#                                            ))
#
#        scene = context.scene
#
#        global_scale = self.global_scale
#        if scene.unit_settings.system != 'NONE' and self.use_scene_unit:
#            global_scale *= scene.unit_settings.scale_length
#
#        global_matrix = axis_conversion(to_forward=self.axis_forward,
#                                        to_up=self.axis_up,
#                                        ).to_4x4() * Matrix.Scale(global_scale, 4)
#
#        faces = itertools.chain.from_iterable(
#            faces_from_mesh(ob, global_matrix, self.use_mesh_modifiers)
#            for ob in context.selected_objects)
#
#        write_roomle_script(faces=faces, **keywords)

        return {'FINISHED'}

def menu_import(self, context):
    self.layout.operator(ImportSTL.bl_idname, text="Stl (.stl)")


def menu_export(self, context):
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".txt"
    self.layout.operator(ExportRoomleScript.bl_idname, text="Roomle Script (.txt)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_import)
    bpy.types.INFO_MT_file_export.append(menu_export)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_import)
    bpy.types.INFO_MT_file_export.remove(menu_export)

if __name__ == "__main__":
    register()
    