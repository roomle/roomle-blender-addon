bl_info = {
    "name": "Roomle Configurator Script",
    "author": "Andreas Atteneder",
    "version": (0, 1, 0),
    "blender": (2, 75, 0),
    "location": "File > Import-Export > Roomle",
    "description": "Export Roomle Configurator Script",
    "warning": "",
    "support": 'COMMUNITY',
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    if "baconx" in locals():
        importlib.reload(baconx)

import os,sys,subprocess
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
    Operator,
    OperatorFileListElement,
    )


# find path for executable
def check_for_exe( name ):
    #check for executable path with where/whereis
    exe_path = None

    find_programs = ('which','where','whereis')

    for find_program in find_programs:
        try:
            exe_path = subprocess.Popen(
                [find_program,name],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception: 
            pass
        else:
            if exe_path is not None:
                stdout,stderr = exe_path.communicate()
                path = str(stdout,'utf-8').rstrip()
                if os.path.isfile(path):
                    print('found {} at {}'.format(name,path))
                    return path

    #check in our path
    for path in sys.path:
        if os.path.exists( os.path.join(path,name) ):
            print('found {} at {}'.format(name,path))
            return os.path.join(path,name)

    return '{} not found!'.format(name)

# Preferences
class ExportRoomleScriptPreferences(bpy.types.AddonPreferences):
   bl_idname = __name__

   corto_exe = bpy.props.StringProperty(
      name="Location of corto executable",
      subtype="FILE_PATH",
      default=check_for_exe('corto')
   )

   def draw(self, context):
      layout = self.layout
      layout.prop(self, 'corto_exe')
      layout.label(text="Pluging will try to auto-find corto, if no path found, or you would like to use a different path, set it here.")

class ExportRoomleScript( Operator, ExportHelper ):
    """Save a Roomle Script from the active object"""
    bl_idname = "export_mesh.roomle_script"
    bl_label = "Export Roomle Script"

    filename_ext = ".txt"
    filter_glob = StringProperty(default="*.txt", options={'HIDDEN'})
    
    use_selection = BoolProperty(
            name="Only Selected Objects",
            description="Export only selected objects on visible layers",
            default=False,
            )

    catalog_id = StringProperty(
        name="Catalog ID",
        description="Catalog name. Used as prefix for mesh and material IDs",
        default='catalog_id',
    )

    # use_scene_unit = BoolProperty(
    #         name="Scene Unit",
    #         description="Apply current scene's unit (as defined by unit scale) to exported data",
    #         default=False,
    #         )
            
    export_normals = BoolProperty(
            name="Export Normals",
            description="Export normals per vertex as well.",
            default=False,
            )
    
    # use_mesh_modifiers = BoolProperty(
    #         name="Apply Modifiers",
    #         description="Apply the modifiers before saving",
    #         default=True,
    #         )
            
    def execute(self, context):
        from mathutils import Matrix, Vector
        from . import baconx
        
        preferences = bpy.context.user_preferences.addons[__name__].preferences

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            "use_scene_unit",
                                            "use_mesh_modifiers",
                                            ))

        global_scale = 1000
        
        global_matrix = axis_conversion(to_forward='-Y',to_up='Z',).to_4x4() * Matrix.Scale(global_scale, 4) * Matrix.Scale(-1,4,Vector((1,0,0)))

        try:
            baconx.write_roomle_script( self, preferences, bpy.context, global_matrix=global_matrix, **keywords)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

def menu_export(self, context):
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".txt"
    self.layout.operator(ExportRoomleScript.bl_idname, text="Roomle Script (.txt)")


def register():
    if not hasattr(bpy.types.Mesh,'export_corto'):
        bpy.types.Mesh.roomle_export_method = bpy.props.EnumProperty(
            name='Roomle script export method',
            default='AUTO',
            items = [
                ('AUTO', 'automatic', 'automatically make bigger meshes external', '', 0),
                ('INTERNAL', 'internal', 'include the mesh as text command', '', 1),
                ('EXTERNAL', 'external', 'load the mesh from external file', '', 2)
                ]
            )

    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_export)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_export)

if __name__ == "__main__":
    register()
    