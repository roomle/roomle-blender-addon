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

import logging
from pathlib import Path
from re import DEBUG
from .scene_handler import SceneHandler
from .material_exporter import export_materials

bl_info = {
    "name": "Roomle Configurator Script",
    "author": "Andreas Atteneder",
    "version": (3, 1, 0),
    "blender": (5, 1, 0),
    "location": "File > Import-Export > Roomle",
    "description": "Export Roomle Configurator Script",
    "support": 'COMMUNITY',
    "category": "Import-Export",
    "tracker_url": "https://servicedesk.roomle.com",
    "warning": "Beta version",
}

if "bpy" in locals():
    import importlib
    importlib.reload(roomle_script)
    importlib.reload(optimize_operator)
else:
    from . import roomle_script
    from . import optimize_operator

import os,sys,subprocess,traceback
import bpy

from bpy.props import (
        StringProperty,
        BoolProperty,
        CollectionProperty,
        EnumProperty,
        FloatProperty,
        IntProperty,
        )
from bpy_extras.io_utils import (
    ExportHelper,
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

    return ''

# Preferences
class ExportRoomleScriptPreferences(bpy.types.AddonPreferences):
   bl_idname = __name__

   corto_exe: bpy.props.StringProperty(
      name="Location of corto executable",
      description="Absolute path of the corto executable. If empty or not found, corto is searched on export",
      subtype="FILE_PATH",
      default=check_for_exe('corto')
   )

   def draw(self, context):
      layout = self.layout
      layout.prop(self, 'corto_exe')
      layout.label(text="If empty or not found, corto is searched on the PATH and in ~/.local/bin, /opt/homebrew/bin and /usr/local/bin.")

class ExportRoomleScript( Operator, ExportHelper ):
    """Save a Roomle Script from the active object"""
    bl_idname = "export_mesh.roomle_script"
    bl_label = "Export Roomle Script"

    filename_ext = ".txt"
    filter_glob: StringProperty(default="*.txt", options={'HIDDEN'})

    catalog_id: StringProperty(
        name="Catalog ID",
        description="Catalog name. Used as prefix for mesh and material IDs",
        default='catalog_id',
    )

    use_file_name_prefix: BoolProperty(
        name="File Name Prefix",
        description="Start the mesh ids and mesh file names with the file name: <file name>_<object>. "
                    "Turn it off to use the object names only",
        default=True,
    )

    use_selection: BoolProperty(
            name="Only Selected Objects",
            description="Export only selected objects on visible layers",
            default=False,
            )
            
    export_normals: BoolProperty(
        name="Export Normals",
        description="Export normals per vertex as well.",
        default=True,
        )

    export_materials: BoolProperty(
        name="Export Materials",
        description="Export roomle material definitions",
        default=False,
        )

    apply_rotations: BoolProperty(
        name="Apply Rotations",
        description="Apply all rotations into vertex data",
        default=True,
        )

    advanced: BoolProperty(
            name="Advanced Settings",
            description="Show advanced settings",
            default=False,
            )

    global_scale: FloatProperty(
        name="Scale",
        description="Multiplier from Blender units to Roomle millimeters. 1000 for scenes modelled in meters, 1 for scenes modelled in millimeters",
        default=1000.0,
        min=0.0001,
        soft_max=1000.0,
        )

    mesh_export_options = [
        ("AUTO", "Automatic", "Automatically make big meshes efficient, external files", 1),
        ("EXTERNAL", "Force Extern", "Export meshes as external files", 2),
        ("INTERNAL", "Force Intern", "Include meshes as text command", 3),
    ]


    use_corto: BoolProperty(
        name="Use Corto",
        description="Compress external meshes into Corto (.crt) files, which replace the OBJ files in the mesh folder. "
                    "Requires the corto executable: set its location in Preferences > Add-ons > Roomle Configurator Script, "
                    "otherwise it is searched on the PATH. Without it, OBJ files are exported",
        default=True,
        )

    mesh_export_option: EnumProperty(
        items=mesh_export_options,
        name="Mesh export method",
        description="Meshes are converted into external files or script commands",
        default="EXTERNAL",
        )

    folder_layout: EnumProperty(
        items=[
            ("UPLOAD", "Upload", "Meshes as <file name>/<mesh id>.crt (or .obj) and materials as CSV for the import into Rubens Admin", 1),
            ("RLCS", "RLCS catalog", "Meshes as <file name>/meshes/<mesh id>/crt_50.crt and materials as <file name>/materials/<material id>/data.json, to copy into a catalog folder of the Rubens Local Content Server", 2),
        ],
        name="Folder layout",
        description="Folder structure of the exported meshes and materials",
        default="UPLOAD",
        )

    uv_float_precision: IntProperty(
        name="UV Precision",
        description="Max floating point fraction precision of UVs in decimal digits when creating script commands",
        default=4,
        min=0,
        max=8
    )

    normal_float_precision: IntProperty(
        name="Normal Precision",
        description="Max floating point fraction precision of Normals in decimal digits when creating script commands",
        default=5,
        min=2,
        max=8
    )
            
    debug: BoolProperty(
            name="Debug mode",
            description="Creates a script that is easier to read and debug for changes/errors.",
            default=False,
            )

    def draw(self, context):
        icon_exp = 'EXPERIMENTAL'
        icon_adv = 'ERROR'
        layout = self.layout
        layout.prop(self, 'catalog_id')
        layout.prop(self, 'use_file_name_prefix')
        layout.prop(self, 'global_scale')
        layout.prop(self, 'use_selection')
        layout.prop(self, 'export_normals')
        layout.prop(self, 'export_materials')
        layout.prop(self, 'apply_rotations')
        layout.prop(self, 'use_corto')
        layout.prop(self, 'folder_layout')
        # TODO: remove warning once it's tested and stable
        if self.apply_rotations:
            layout.label(text='Apply rotation is experimental',icon=icon_exp)
        layout.prop(self, 'advanced') 
        if self.advanced:
            box=layout.box()
            box.label(text='Advanced',icon=icon_adv)
            box.prop(self, 'mesh_export_option')
            # box.prop(self, 'mesh_format_option')
            box.prop(self, 'uv_float_precision')
            box.prop(self, 'normal_float_precision')

    def execute(self, context):
        # Scripts (e.g. Blender MCP running code from a timer) can call the operator without a window,
        # but the material export needs one to switch to the copied export scene.
        if context.window is None and context.window_manager.windows:
            with context.temp_override(window=context.window_manager.windows[0]):
                return self.export_roomle_script(bpy.context)
        return self.export_roomle_script(context)

    def export_roomle_script(self, context):
        from mathutils import Matrix, Vector
        from . import roomle_script


        preferences = context.preferences.addons[__name__].preferences

        if self.filepath == '':
            raise Exception('no filepath provided')

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "check_existing",
                                            "filter_glob",
                                            "use_scene_unit",
                                            "use_mesh_modifiers",
                                            "advanced"
                                            ))
        # collected during the export, reported to the user at the end
        warnings = []
        keywords['warnings'] = warnings
        keywords['corto_exe'] = roomle_script.get_corto_exe(preferences) if self.use_corto else None

        if self.folder_layout == 'RLCS' and self.catalog_id in ('', 'catalog_id'):
            warnings.append('Set the Catalog ID to the name of the catalog folder: the Rubens Local Content Server finds meshes and materials by their catalog.')

        mat_axis = axis_conversion(to_forward='-Y',to_up='Z',).to_4x4()
        mat_global_scale = Matrix.Scale(self.global_scale, 4)
        mat_flip = Matrix.Scale(-1,4,Vector((1,0,0)))

        global_matrix = mat_axis @ mat_global_scale @ mat_flip

        # the export selects temporary objects, the selection of the user is restored afterwards
        original_scene, view_layer_name = context.scene, context.view_layer.name
        selected_object_names = {obj.name for obj in context.selected_objects}
        active_object_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

        scene_handler = None
        try:
            if keywords['export_materials']:
                scene_handler = SceneHandler(context.scene)
                scene_handler.copy_scene()
                export_materials(**keywords)

            roomle_script.write_roomle_script( self, preferences, context, global_matrix=global_matrix, **keywords)
        except Exception as e:
            # printed for scripts and agents reading the console, reported for the user in the UI
            traceback.print_exc()
            message = f'Roomle export failed: {e}'
            print(message)
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
        finally:
            if scene_handler:
                scene_handler.remove_export_scene()
            # looked up again, the export scene of the material export changes the context
            view_layer = original_scene.view_layers[view_layer_name]
            for obj in view_layer.objects:
                # entries of removed temporary objects stay empty until the view layer is synced
                if obj is not None:
                    obj.select_set(obj.name in selected_object_names, view_layer=view_layer)
            view_layer.objects.active = view_layer.objects.get(active_object_name) if active_object_name else None

        for warning in dict.fromkeys(warnings):
            print(f'Roomle export warning: {warning}')
            self.report({'WARNING'}, warning)

        return {'FINISHED'}


def menu_export(self, context):
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".txt"
    self.layout.operator(ExportRoomleScript.bl_idname, text="Roomle Script (.txt)")



def register():
    # Logging
    # TODO: add logging handler
    # Blender
    bpy.utils.register_class(ExportRoomleScript)
    bpy.utils.register_class(ExportRoomleScriptPreferences)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)
    optimize_operator.register()

def unregister():
    optimize_operator.unregister()
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    bpy.utils.unregister_class(ExportRoomleScriptPreferences)
    bpy.utils.unregister_class(ExportRoomleScript)

if __name__ == "__main__":
    register()
    