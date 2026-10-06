'''
Writes materials in the folder structure of the Rubens Local Content Server (RLCS):
<materials dir>/<material id>/data.json and its textures next to it, named by their mapping (RGB.png, XYZ.png, ...).
'''
from __future__ import annotations

import json
import zlib
from pathlib import Path
from typing import Iterable, Optional, Tuple

import bpy
import numpy as np

from io_mesh_roomle.material_exporter import pbr_2_material_definition
from io_mesh_roomle.material_exporter._exporter import BlenderMaterialForExport
from io_mesh_roomle.material_exporter.utils.materials import get_principled_bsdf_input

# Roomle accepts PNG and JPEG textures, the files are written as they are
IMAGE_SIGNATURES = {b'\x89PNG': 'png', b'\xff\xd8': 'jpg'}
TEXTURE_MAPPINGS = ('RGB', 'RGBA', 'XYZ', 'ORM')


def write_rlcs_materials(material_exports: Iterable[BlenderMaterialForExport], materials_dir: Path, catalog_id: str, warnings: list):
    for material_export in material_exports:
        write_rlcs_material(material_export, materials_dir / material_export.name, catalog_id, warnings)


def write_rlcs_material(material_export: BlenderMaterialForExport, material_dir: Path, catalog_id: str, warnings: list):
    pbr = material_export.pbr
    material_id = f'{catalog_id}:{material_export.name}'
    shading = pbr_2_material_definition(material_export).shading

    material_dir.mkdir(parents=True, exist_ok=True)
    # the mapping of a texture can change between exports (e.g. RGB -> RGBA)
    for file in material_dir.iterdir():
        if file.is_file() and file.stem in TEXTURE_MAPPINGS:
            file.unlink()

    textures = []
    alpha_mode = 'BLEND' if shading.alpha < 1 else None
    if pbr.diffuse.map:
        mapping = 'RGB'
        alpha = alpha_image(material_export)
        if alpha and has_transparency(alpha):
            if image_source(alpha) == image_source(pbr.diffuse.map):
                mapping = 'RGBA'
                alpha_mode = 'BLEND'
            else:
                warnings.append(f'Material {material_export.material.name}: the alpha of a separate image is not exported.')
        textures.append((pbr.diffuse.map, mapping))
    if pbr.normal.map:
        textures.append((pbr.normal.map, 'XYZ'))
    if pbr.roughness.map:
        textures.append((pbr.roughness.map, 'ORM'))

    texture_objects = []
    for image, mapping in textures:
        file_name = write_texture(image, material_dir, mapping, warnings)
        if not file_name:
            continue
        mm_width, mm_height = texture_size_mm(material_export, image, warnings)
        texture_objects.append({
            # local textures have no Rubens Admin id, a stable checksum keeps them apart
            'id': zlib.crc32(f'{material_id}:{mapping}'.encode('utf-8')),
            'material': material_id,
            'image': f'@material/{file_name}',
            'mmWidth': mm_width,
            'mmHeight': mm_height,
            'tileable': True,
            'mapping': mapping,
        })

    shading_json = {
        'version': '2.0.0',
        'basecolor': {'r': shading.basecolor.r, 'g': shading.basecolor.g, 'b': shading.basecolor.b},
        'roughness': shading.roughness,
        'metallic': shading.metallic,
        'alpha': shading.alpha,
        'transmission': shading.transmission,
        'transmissionIOR': shading.transmissionIOR,
        'doubleSided': shading.doubleSided,
    }
    if alpha_mode:
        shading_json['alphaMode'] = alpha_mode

    definition = {
        'externalIdentifier': material_export.name,
        'label': material_export.material.name,
        'catalog': catalog_id,
        'id': material_id,
        'shading': shading_json,
        'textures': [texture['id'] for texture in texture_objects],
        'textureObjects': texture_objects,
        'active': True,
    }
    with open(material_dir / 'data.json', 'w', encoding='utf-8') as file:
        json.dump(definition, file, indent=4, ensure_ascii=False)
        file.write('\n')


def write_texture(image: bpy.types.Image, folder: Path, mapping: str, warnings: list) -> Optional[str]:
    '''writes the packed or source file of the image unchanged, returns the file name'''
    data = bytes(image.packed_file.data) if image.packed_file else None
    source = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
    if data is None and source and source.is_file():
        data = source.read_bytes()
    if data is None:
        warnings.append(f'Texture {image.name} has no image file and was not exported.')
        return None

    extension = next((ext for signature, ext in IMAGE_SIGNATURES.items() if data.startswith(signature)), None)
    if extension is None:
        warnings.append(f'Texture {image.name} is not a PNG or JPEG file and was not exported.')
        return None

    file_name = f'{mapping}.{extension}'
    (folder / file_name).write_bytes(data)
    return file_name


def texture_size_mm(material_export: BlenderMaterialForExport, image: bpy.types.Image, warnings: list) -> Tuple[float, float]:
    '''
    Size of one texture repetition in mm. UV coordinates are texture coordinates in mm in Roomle, so 1 mm per UV unit
    shows the texture like Blender does without a Mapping node.
    '''
    for node in material_export.used_tex_nodes:
        vector = node.inputs['Vector']
        if node.image != image or not vector.is_linked:
            continue
        mapping = vector.links[0].from_node
        if not isinstance(mapping, bpy.types.ShaderNodeMapping):
            continue
        scale = mapping.inputs['Scale']
        if scale.is_linked or not scale.default_value[0] or not scale.default_value[1]:
            warnings.append(f'Material {material_export.material.name}: unsupported Mapping node scale, exported with 1 mm per UV unit.')
            return 1.0, 1.0
        location = mapping.inputs.get('Location')
        if any(mapping.inputs['Rotation'].default_value) or (location and location.enabled and any(location.default_value)):
            warnings.append(f'Material {material_export.material.name}: location and rotation of the Mapping node are not exported.')
        scale_x, scale_y = scale.default_value[0], scale.default_value[1]
        if mapping.vector_type == 'TEXTURE':
            # texture type applies the inverse transformation
            return round(scale_x, 4), round(scale_y, 4)
        return round(1 / scale_x, 4), round(1 / scale_y, 4)
    return 1.0, 1.0


def alpha_image(material_export: BlenderMaterialForExport) -> Optional[bpy.types.Image]:
    '''image whose alpha output is connected to the alpha of the Principled BSDF'''
    socket = get_principled_bsdf_input(material_export.used_principled_bsdf_shader, 'Alpha')
    if not socket.is_linked:
        return None
    link = socket.links[0]
    if isinstance(link.from_node, bpy.types.ShaderNodeTexImage) and link.from_socket.name == 'Alpha':
        return link.from_node.image
    return None


def has_transparency(image: bpy.types.Image) -> bool:
    '''
    Importers often connect the alpha of opaque textures. Checks a downscaled copy, because
    reading the pixels of big textures is slow.
    '''
    probe = image.copy()
    try:
        probe.scale(256, 256)
        pixels = np.empty(len(probe.pixels), dtype=np.float32)
        probe.pixels.foreach_get(pixels)
        return bool((pixels[3::4] < 0.99).any())
    finally:
        bpy.data.images.remove(probe)


def image_source(image: bpy.types.Image) -> str:
    '''images loaded twice (e.g. once as color and once as non-color data) share their file'''
    return bpy.path.abspath(image.filepath) if image.filepath else image.name
