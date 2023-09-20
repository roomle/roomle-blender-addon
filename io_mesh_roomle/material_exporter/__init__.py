import logging
import bpy
from pathlib import Path
from typing import Iterable, List, Union, TYPE_CHECKING

from io_mesh_roomle.material_exporter._exporter import BlenderMaterialForExport, TextureNameManager
from io_mesh_roomle.material_exporter._roomle_material_csv import MaterialDefinition, RoomleMaterialsCsv

log = logging.getLogger('legacy csv')
log.setLevel(logging.DEBUG)


def split_object_by_materials(obj: bpy.types.Object) -> set[bpy.types.Object]:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    # obj.name = get_valid_name(obj.name)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.editmode_toggle()

    return set(bpy.context.selected_objects)


def pbr_2_material_definition(data: BlenderMaterialForExport) -> MaterialDefinition:

    def zip_path(value: Union[str, None, bpy.types.Image]):

        pass
        # if isinstance(value, bpy.types.Image):
        if value is None:
            return ''
        # return 'zip://' + value.rsplit('/')[-1]
        # return value.replace('//textures/', 'zip://')
        return f'zip://{value}'

    def prec(value: Union[float, None, tuple[float]], default: float):
        if value is None:
            return default
        return round(value, 2)

    pbr = data.pbr
    md = MaterialDefinition()

    md.material_id = data.name
    md.label_en = data.name
    md.label_de = data.name

    md.shading.alpha = prec(pbr.alpha.default_value,
                            1)                # type: ignore
    md.shading.roughness = prec(
        pbr.roughness.default_value, 0.5)      # type: ignore
    md.shading.metallic = prec(
        pbr.metallic.default_value, 0)          # type: ignore

    log.debug(f'🍕 {data.material.name}')
    log.debug(f'diffuse: {pbr.diffuse.default_value}')
    md.shading.basecolor.set(*pbr.diffuse.default_value)               # type: ignore


    md.shading.transmission = prec(
        pbr.transmission.default_value, 0)  # type: ignore
    
    log.debug(f'ior: {pbr.ior.default_value}')
    md.shading.transmissionIOR = prec(
        pbr.ior.default_value, 1.5)      # type: ignore

    # md.diffuse_map.image = zip_path(pbr.diffuse.map)
    md.diffuse_map.image = zip_path(pbr.diffuse.map)
    md.diffuse_map.mapping = "RGB" if zip_path(pbr.diffuse.map) != '' else ''

    md.normal_map.image = zip_path(pbr.normal.map)
    md.normal_map.mapping = "XYZ" if zip_path(pbr.normal.map) != '' else ''

    md.orm_map.image = zip_path(pbr.roughness.map)
    md.orm_map.mapping = "ORM" if zip_path(pbr.roughness.map) != '' else ''
    return md


def get_mesh_objects_for_export(use_selection: bool = False) -> set[bpy.types.Object]:
    data = set()
    obj_list = bpy.context.selected_objects if use_selection else bpy.context.scene.objects
    for obj in obj_list:
        if obj.type == 'MESH':
            data.add(obj)
    return data


def get_materials_used_by_objs(objects: Iterable[bpy.types.Object]) -> set:
    data = set()
    for obj in objects:
        for slot in obj.material_slots:
            if slot.material:
                data.add(slot.material)
    return data



def export_materials(**keywords):

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

    out_path = Path(keywords['filepath']).parent
    use_selection = keywords["use_selection"]

    csv_exporter = RoomleMaterialsCsv()
    texture_name_manager = TextureNameManager()


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

    materials = get_materials_used_by_objs(mesh_objs_to_export)

    material_exports: list[BlenderMaterialForExport]= [
        BlenderMaterialForExport(material)
        for material in materials
    ]

    for m in material_exports:
        m.pbr = PBR_ShaderData(m.material)
        pass
        for channel in m.pbr.all_pbr_channels:
            channel.map = texture_name_manager.validate_name(channel.map)
        for tex in m.used_tex_nodes:
            name = texture_name_manager.validate_name(tex.image)
            tex.image.save(filepath=str(out_path / 'materials' / name))


    for mat in material_exports:
        csv_exporter.add_material_definition(
            pbr_2_material_definition(mat)
        )
    csv_exporter.write(out_path / 'materials/materials.csv')

    # ==================================================

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs_to_export:  # | selection_to_restore:
        obj.select_set(True)
