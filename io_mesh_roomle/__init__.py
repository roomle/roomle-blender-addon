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
from pathlib import Path
sys.path.append(str(Path(__file__).parent.absolute() / 'external-packages'))

import subprocess
import os
from bpy.types import (
    Operator,
    OperatorFileListElement,
)
from bpy_extras.io_utils import (
    ExportHelper,
    axis_conversion
)
from bpy.props import (
    StringProperty,
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
)
import bpy
from io_mesh_roomle import arguments, material_exporter, scene_handler
import json
import shutil

import zipfile

from io_mesh_roomle.csv_handler import _CSV_DictHandler
from io_mesh_roomle.enums import COMP_CSV_COLS, FILE_NAMES, ITEMS_CSV_COLS, META_JSON_FIELDS


bl_info = {
    "name": "Roomle Configurator Script",
    "author": "Andreas Atteneder",
    "version": (3, 0, 0),
    "blender": (3, 6, 2),
    "location": "File > Import-Export > Roomle",
    "description": "Export Roomle Configurator Script",
    "support": 'COMMUNITY',
    "category": "Import-Export",
    "tracker_url": "https://servicedesk.roomle.com",
    "warning": "Beta version",
}

from io_mesh_roomle import roomle_script
from io_mesh_roomle import optimize_operator

if "bpy" in locals():
    import importlib
    importlib.reload(roomle_script)
    importlib.reload(optimize_operator)


# find path for executable
def check_for_exe(name):
    # check for executable path with where/whereis
    exe_path = None

    find_programs = ('which', 'where', 'whereis')

    for find_program in find_programs:
        try:
            exe_path = subprocess.Popen(
                [find_program, name],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception:
            pass
        else:
            if exe_path is not None:
                stdout, stderr = exe_path.communicate()
                path = str(stdout, 'utf-8').rstrip()
                if os.path.isfile(path):
                    print('found {} at {}'.format(name, path))
                    return path

    # check in our path
    for path in sys.path:
        if os.path.exists(os.path.join(path, name)):
            print('found {} at {}'.format(name, path))
            return os.path.join(path, name)

    return '{} not found!'.format(name)

# Preferences


class ExportRoomleScriptPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    corto_exe: bpy.props.StringProperty(  # type: ignore
        name="Location of corto executable",
        subtype="FILE_PATH",
        default=check_for_exe('corto')
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'corto_exe')
        layout.label(
            text="Pluging will try to auto-find corto, if no path found, or you would like to use a different path, set it here.")


class ExportRoomleScript(Operator, ExportHelper):
    """Save a Roomle Script from the active object"""
    bl_idname = "export_mesh.roomle_script"
    bl_label = "Export Roomle Script"

    # TODO: 0d9bf2c5 bundle in .roomle file
    # filename_ext = ".roomle"
    filename_ext = ".txt"
    filter_glob: StringProperty(
        default="*.txt", options={'HIDDEN'})  # type: ignore

    catalog_id: StringProperty(  # type: ignore
        name="Catalog ID",
        description="Catalog name. Used as prefix for mesh and material IDs",
        default='catalog_id',
    )

    use_selection: BoolProperty(  # type: ignore
        name="Only Selected Objects",
        description="Export only selected objects on visible layers",
        default=False,
    )

    export_normals: BoolProperty(  # type: ignore
        name="Export Normals",
        description="Export normals per vertex as well.",
        default=True,
    )

    export_materials: BoolProperty(  # type: ignore
        name="Export Materials",
        description="Export roomle material definitions",
        default=False,
    )

    apply_rotations: BoolProperty(  # type: ignore
        name="Apply Rotations",
        description="Apply all rotations into vertex data",
        default=True,
    )

    advanced: BoolProperty(  # type: ignore
        name="Advanced Settings",
        description="Show advanced settings",
        default=False,
    )

    mesh_export_options = [
        ("AUTO", "Automatic", "Automatically make big meshes efficient, external files", 1),
        ("EXTERNAL", "Force Extern", "Include meshes as text command", 2),
        ("INTERNAL", "Force Intern", "Export meshes as external files", 3),
    ]

    use_corto: BoolProperty(  # type: ignore
        name="Use Corto",
        description="Create corto files if possible",
        default=True,
    )

    mesh_export_option: EnumProperty(  # type: ignore
        items=mesh_export_options,
        name="Mesh export method",
        description="Meshes are converted into external files or script commands",
        default="AUTO",
    )

    uv_float_precision: IntProperty(  # type: ignore
        name="UV Precision",
        description="Max floating point fraction precision of UVs in decimal digits when creating script commands",
        default=4,
        min=0,
        max=8
    )

    normal_float_precision: IntProperty(  # type: ignore
        name="Normal Precision",
        description="Max floating point fraction precision of Normals in decimal digits when creating script commands",
        default=5,
        min=2,
        max=8
    )

    debug: BoolProperty(  # type: ignore
        name="Debug mode",
        description="Creates a script that is easier to read and debug for changes/errors.",
        default=False,
    )

    def draw(self, context):
        icon_exp = 'EXPERIMENTAL'
        icon_adv = 'ERROR'
        layout = self.layout
        layout.prop(self, 'catalog_id')
        layout.prop(self, 'use_selection')
        layout.prop(self, 'export_normals')
        layout.prop(self, 'export_materials')
        layout.prop(self, 'apply_rotations')
        layout.prop(self, 'use_corto')
        # TODO: remove warning once it's tested and stable
        if self.apply_rotations:
            layout.label(text='Apply rotation is experimental', icon=icon_exp)
        layout.prop(self, 'advanced')
        if self.advanced:
            box = layout.box()
            box.label(text='Advanced', icon=icon_adv)
            box.prop(self, 'mesh_export_option')
            # box.prop(self, 'mesh_format_option')
            box.prop(self, 'uv_float_precision')
            box.prop(self, 'normal_float_precision')

    @property
    def addon_arguments(self) -> arguments.ArgsStore:
        addon_args_as_dict: dict = self.as_keywords()  # type: ignore
        addon_args_as_dict['component_id'] = (
            os.path
            .splitext(addon_args_as_dict['filepath'])[0]
            .split('/')[-1]
        )

        # Mashumaro acts as a white list which parameters get added
        args = arguments.ArgsStore.from_dict(addon_args_as_dict)

        not_used = tuple(set(addon_args_as_dict.keys()) -
                         set(args.to_dict().keys()))
        pass

        return args

    def execute(self, context):
        from mathutils import Matrix, Vector
        from . import roomle_script

        preferences = bpy.context.preferences.addons[__name__].preferences

        if self.filepath == '':
            raise Exception('no filepath provided')

        addon_args = self.addon_arguments

        if addon_args.export_materials:
            scn_hndlr = scene_handler.SceneHandler(bpy.context.scene)
            scn_hndlr.copy_scene()
            material_exporter.export_materials(addon_args)

        global_scale = 1000

        mat_axis = axis_conversion(to_forward='-Y', to_up='Z',).to_4x4()
        mat_global_scale = Matrix.Scale(global_scale, 4)
        mat_flip = Matrix.Scale(-1, 4, Vector((1, 0, 0)))

        global_matrix = mat_axis @ mat_global_scale @ mat_flip

        try:
            roomle_script.write_roomle_script(
                self, preferences, bpy.context, global_matrix=global_matrix, addon_args=addon_args)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        if addon_args.export_materials:
            # bpy.ops.wm.save_as_mainfile(filepath='/Users/clemens/Dev/git/DAP-AssetFactory/tmp/snap.blend')
            scn_hndlr.remove_export_scene()  # type: ignore

        # TODO: add argument for this

        # TODO: add width and height to product csv
        prod_handler = _CSV_DictHandler()
        prod_handler.add_row(
            {
                ITEMS_CSV_COLS.ITEM_ID: addon_args.product_id,
                ITEMS_CSV_COLS.CONFIGURATION: json.dumps({"componentId": addon_args.product_ext_id}),
                ITEMS_CSV_COLS.VISIBILITY_STATUS: 0,
            }
        )
        prod_handler.write(addon_args.export_dir / 'items.csv')

        comp_handler = _CSV_DictHandler()
        for comp_file in addon_args.components_dir.glob('*.json'):
            data = json.load(comp_file.open())
            comp_handler.add_row(
                {
                    COMP_CSV_COLS.COMPONENT_ID: data['id'].split(':')[-1],
                    COMP_CSV_COLS.COMPONENT_DEFINITION: f"zip://{comp_file.name}",
                    COMP_CSV_COLS.VISIBILITY_STATUS: 0,
                }
            )
        comp_handler.write(addon_args.components_dir / 'components.csv')

        # ==================[ ZIP UP STUFF ]==================

        output_dir = addon_args.export_dir

        # Materials
        materials_dir = addon_args.materials_dir
        if materials_dir.exists() and materials_dir.is_dir():
            with zipfile.ZipFile(output_dir / 'materials.zip', 'w') as zf:
                for file in (materials_dir.rglob("*")):
                    zf.write(file, file.name)
            shutil.rmtree(materials_dir)

        # Meshes

        meshes_dir = addon_args.meshes_dir
        if meshes_dir.exists() and meshes_dir.is_dir():
            with zipfile.ZipFile(output_dir / 'meshes.zip', 'w') as zf:
                for file in (meshes_dir.rglob("*")):
                    if file.suffix.lower == '.txt' or file.is_dir():
                        continue
                    zf.write(file, file.name)

            shutil.rmtree(meshes_dir)

        # Components

        comp_dir = addon_args.components_dir
        if comp_dir.exists() and comp_dir.is_dir():
            with zipfile.ZipFile(output_dir / 'components.zip', 'w') as zf:
                for file in (comp_dir.rglob("*")):
                    if file.suffix.lower == '.txt' or file.is_dir():
                        continue
                    zf.write(file, file.name)

            shutil.rmtree(comp_dir)

        # ====================================================

        # fmt: off
        (addon_args.export_dir / FILE_NAMES.META_JSON).write_text(json.dumps({
                        META_JSON_FIELDS.TARGET_ID:  addon_args.product_ext_id,
                        META_JSON_FIELDS.MATERIALS:  FILE_NAMES.MATERIALS_ZIP,
                        META_JSON_FIELDS.MESHES:     FILE_NAMES.MESHES_ZIP,
                        META_JSON_FIELDS.COMPONENTS: FILE_NAMES.COMPONENTS_ZIP,
                        META_JSON_FIELDS.ITEMS:      FILE_NAMES.ITEMS_CSV,
                        META_JSON_FIELDS.TAGS:       FILE_NAMES.TAGS_CSV
                        }, indent=4))
        # fmt: on

        # TODO: 0d9bf2c5 bundle in .roomle file

        return {'FINISHED'}


def menu_export(self, context):
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".txt"
    self.layout.operator(ExportRoomleScript.bl_idname,
                         text="Roomle Script (.txt)")


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
