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

import sys

# Installing the add-on again without restarting Blender reloads only this file, its submodules would keep the
# code of the previous version. They are removed, so the imports below load the new code.
if "bpy" in locals():
    for module_name in [name for name in sys.modules if name.startswith(__name__ + '.')]:
        del sys.modules[module_name]

import logging
from pathlib import Path
from re import DEBUG
from .scene_handler import SceneHandler
from .material_exporter import export_materials

bl_info = {
    "name": "Roomle Configurator Script",
    "author": "Andreas Atteneder",
    "version": (3, 2, 0),
    "blender": (5, 1, 0),
    "location": "File > Import-Export > Roomle",
    "description": "Export Roomle Configurator Script",
    "support": 'COMMUNITY',
    "category": "Import-Export",
    "tracker_url": "https://servicedesk.roomle.com",
    "warning": "Alpha build 3.2.0-alpha.1",
}

from . import roomle_script
from . import optimize_operator

import os,re,subprocess,traceback
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
        description="Catalog of the mesh and material IDs in the script. The RLCS formats use the name of the folder the file is saved in instead",
        default='catalog_id',
    )

    use_file_name_prefix: BoolProperty(
        name="File Name as Prefix",
        description="Start the mesh ids and mesh file names with the file name: <file name>_<object>. "
                    "Turn it off to use the object names only",
        default=True,
    )

    output_format: EnumProperty(
        items=[
            ("OBJ", "OBJ", "External meshes as Wavefront OBJ files: <file name>/<mesh id>.obj", 1),
            ("CORTO", "Corto", "External meshes as Corto files with the same names: <file name>/<mesh id>.crt. "
                "Requires the corto executable: set its location in Preferences > Add-ons > Roomle Configurator Script, "
                "otherwise it is searched on the PATH. Without it, OBJ files are exported", 2),
            ("RLCS", "RLCS", "Corto meshes for the Rubens Local Content Server: save the file into the catalog folder "
                "content/<catalog id>/, its name is the catalog id and the meshes are written next to it as "
                "meshes/<mesh id>/crt_50.crt", 3),
            ("RLCS_MATERIALS", "RLCS with materials", "Like RLCS, and the materials are written next to the file as "
                "materials/<material id>/data.json with their textures", 4),
        ],
        name="Output Format",
        description="File format and folder structure of the external meshes",
        default="OBJ",
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


    # replaced by output_format, kept for scripts calling the operator with use_corto=True
    use_corto: BoolProperty(
        name="Use Corto",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
        )

    mesh_export_option: EnumProperty(
        items=mesh_export_options,
        name="Mesh export method",
        description="Meshes are converted into external files or script commands",
        default="EXTERNAL",
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
        layout.prop(self, 'output_format')
        if self.output_format in ('RLCS', 'RLCS_MATERIALS'):
            # the catalog is the folder the file is saved in: content/<catalog id>/
            catalog_folder = os.path.basename(os.path.dirname(self.filepath)) if self.filepath else ''
            layout.label(text=f'Catalog ID: {catalog_folder or "name of the folder"} (folder of the file)', icon='FILE_FOLDER')
        else:
            layout.prop(self, 'catalog_id')
        row = layout.row()
        # only external meshes have ids
        row.enabled = self.mesh_export_option != 'INTERNAL'
        row.prop(self, 'use_file_name_prefix')
        layout.prop(self, 'global_scale')
        layout.prop(self, 'use_selection')
        layout.prop(self, 'export_normals')
        if self.output_format in ('OBJ', 'CORTO'):
            # the RLCS formats choose the materials by the format
            layout.prop(self, 'export_materials')
        layout.prop(self, 'apply_rotations')
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

        # the export steps read these options derived from the output format
        output_format = 'CORTO' if self.use_corto and self.output_format == 'OBJ' else self.output_format
        rlcs = output_format in ('RLCS', 'RLCS_MATERIALS')
        keywords['use_corto'] = output_format != 'OBJ'
        keywords['folder_layout'] = 'RLCS' if rlcs else 'UPLOAD'
        keywords['export_materials'] = output_format == 'RLCS_MATERIALS' or (not rlcs and self.export_materials)
        keywords['corto_exe'] = roomle_script.get_corto_exe(preferences) if keywords['use_corto'] else None

        if rlcs:
            # the catalog is the folder the file is saved in: content/<catalog id>/
            catalog_folder_path = os.path.dirname(os.path.abspath(self.filepath))
            catalog_id = os.path.basename(catalog_folder_path)
            if not re.fullmatch(r'[A-Za-z0-9_-]+', catalog_id):
                message = (f'Roomle export failed: save the file into a catalog folder content/<catalog id>/, '
                           f'the folder name "{catalog_id}" is not a valid catalog id.')
                print(message)
                self.report({'ERROR'}, message)
                return {'CANCELLED'}
            if os.path.basename(os.path.dirname(catalog_folder_path)) != 'content':
                warnings.append(f'The file is not saved in a catalog folder content/<catalog id>/, '
                                f'the folder name {catalog_id} is used as catalog id.')
            # values remembered from an earlier export are ignored, only a Catalog ID passed by a script is reported
            if self.properties.is_property_set('catalog_id', ghost=False) and self.catalog_id != catalog_id:
                warnings.append(f'The Catalog ID {self.catalog_id} is not used by the RLCS formats, '
                                f'the catalog is the folder name {catalog_id}.')
            keywords['catalog_id'] = catalog_id

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
    