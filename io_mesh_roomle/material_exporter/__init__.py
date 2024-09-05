# - [ ] Handle Multi user materials more elegantly
# - [ ] fix tests
# - [ ] write tests for different export scenearios


import logging
import bpy

from pathlib import Path
from typing import Any, Generator, Iterable, Union
from io_mesh_roomle import arguments
from io_mesh_roomle.enums import FILE_NAMES, MATERIALS_CSV_COLS

from io_mesh_roomle.material_exporter._exporter import BlenderMaterialForExport, TextureNameManager
from io_mesh_roomle.material_exporter._roomle_material_csv import MaterialDefinition, CSV_ByDicts

log = logging.getLogger('legacy csv')
log.setLevel(logging.DEBUG)


def split_object_by_materials(obj: bpy.types.Object) -> set[bpy.types.Object]:

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.editmode_toggle()

    return set(bpy.context.selected_objects)


class MaterialCSVRow:
    def __init__(self) -> None:
        self.data_dict: dict = {}
        self._image_index: int = -1

    def add_texture_field(
        self,
        tex_image: str,
        tex_mapping: str,
        tex_mmwidth: float = 1,
        tex_mmheight: float = 1,
        tex_tileable: bool = True,
    ) -> None:
        if not tex_image:
            return

        self._image_index += 1
        csv_col_add_index = lambda x: x.format(**{"index": self._image_index})

        self.data_dict.update(
            {
                csv_col_add_index(MATERIALS_CSV_COLS.TEX_IMAGE): tex_image,
                csv_col_add_index(MATERIALS_CSV_COLS.TEX_MAPPING): tex_mapping,
                csv_col_add_index(MATERIALS_CSV_COLS.TEX_MMWIDTH): tex_mmwidth,
                csv_col_add_index(MATERIALS_CSV_COLS.TEX_MMHEIGHT): tex_mmheight,
                csv_col_add_index(MATERIALS_CSV_COLS.TEX_TILEABLE): tex_tileable,
            }
        )

    def set_field(self, key, value) -> None:
        """set a single field in the csv

        Args:
            key (str): column name
            value (str, float, int): value in this row
        """
        self.data_dict.update({key: value})


def get_mesh_objects_for_export(use_selection: bool = False) -> set[bpy.types.Object]:
    data = set()
    obj_list = bpy.context.selected_objects if use_selection else bpy.context.scene.objects
    for obj in obj_list:
        if obj.type == 'MESH':
            data.add(obj)
    return data


def get_materials_used_by_objs(
    objects: Iterable[bpy.types.Object],
) -> Generator[bpy.types.Material, Any, Any]:
    """generator returning all unique materials used by objects.
    If a material is used in multiple objects the material will only
    be yielded once!

    Args:
        objects (Iterable[bpy.types.Object]): blender objects to check

    Yields:
        Generator[bpy.types.Material,Any,Any]: generator
    """
    _material_register = set()
    for obj in objects:
        for slot in obj.material_slots:
            if slot.material and slot.material not in _material_register:
                _material_register.add(slot.material)
                yield slot.material


def export_materials(addon_args: arguments.ArgsStore):

    log.info(f"\n{'='*80}\n{'STARTING MATERIAL EXPORT':^80}\n{'='*80}")
    # Rough outline
    # * copy scene
    # * separate objects
    # * analyze materials
    # * save images
    # * create csv
    # * delete scene

    # get the objects to export
    from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ShaderData

    out_path = Path(addon_args.filepath).parent
    use_selection = addon_args.use_selection

    log.info(f"\n{('*'*30):^80}\n{'get mesh objects':^80}\n{('*'*30):^80}")

    mesh_objs_to_export = get_mesh_objects_for_export(use_selection)

    # ------------- [ separate objects by materials ] --------------
    extracted_meshes = set()
    for obj in mesh_objs_to_export:
        material_parts = split_object_by_materials(obj)
        # add new mesh fragments to export
        extracted_meshes.update(material_parts)
    mesh_objs_to_export.update(extracted_meshes)

    # ==================================================

    materials_for_export: list[BlenderMaterialForExport] = [
        BlenderMaterialForExport(material, addon_args.component_id)
        for material in get_materials_used_by_objs(mesh_objs_to_export)
    ]

    texture_name_manager = TextureNameManager()
    for blender_mat_for_export in materials_for_export:
        for channel in blender_mat_for_export.pbr.all_pbr_channels:
            channel.map = texture_name_manager.validate_name(channel.map)
        for tex in blender_mat_for_export.used_tex_nodes:
            name = texture_name_manager.validate_name(tex.image)
            tex.image.save(filepath=str(out_path / "materials" / name))

    material_csv = CSV_ByDicts()
    for mat_for_export in materials_for_export:
        material_csv.add_row(mat_for_export.csv_dict)

    material_csv.write_csv((out_path / "materials") / FILE_NAMES.MATERIALS_CSV)

    # ==================================================

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs_to_export:  # | selection_to_restore:
        obj.select_set(True)
