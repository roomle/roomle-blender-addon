from __future__ import annotations
from typing import Iterable, List, Protocol, Tuple, Union

import io_mesh_roomle.material_exporter.utils.materials as utils_materials
import dataclasses
import bpy

from io_mesh_roomle.material_exporter.utils import color as utils_color
from io_mesh_roomle import enums


# def unpack_images(self, texture_name_manager: TextureNameManager):
#     """unpack the images of all used `ShaderNodeTexImage` and prpend the material name
#     """

#     # TODO: manage external images with same name. rather use `node.image.name` as file name

#     for node in [node for node in self.used_nodes if isinstance(node, bpy.types.ShaderNodeTexImage)]:
#         name = texture_name_manager.validate_name(node.image)
#         node.image.save(filepath=str(self.out_path / 'materials' / name))


class ObjectToRegister(Protocol):
    """eg bpy.types.Image"""
    file_format: str
    name: str


class TextureNameManager:
    """keeps track of image file name used to avoid overwriting of texture files using the same name
    """

    def __init__(self) -> None:
        # imagenode_id : filename
        self.images_by_id = {}

        # filename : imagenode_id
        self.names = {}

    def validate_name(self, image: ObjectToRegister) -> str | None:
        """returns a valid name by checking the requested name against already used ones.
        also registers the name in the class dictionaries

        Args:
            image (bpy.types.Image): the image node to check
            name_to_use (str): the desired name

        Returns:
            str: a valid filename without the path
        """
        if image is None:
            return None
        file_format = image.file_format
        if not file_format in enums.SUPPORTED_TEXTURE_FILE_FORMATS:
            raise Exception(f'unsupported texture type {file_format}')

        suffix = enums.SUPPORTED_TEXTURE_FILE_FORMATS[image.file_format]
        if image.name.endswith(suffix):
            name_to_use = image.name
        else:
            name_to_use = f'{image.name}{suffix}'
        img_id = id(image)

        name_key = name_to_use.lower()

        if img_id in self.images_by_id.keys():
            return self.images_by_id[img_id]

        if name_key in self.names.keys() and self.names[name_key] != id(image):
            name_to_use = f'({image.name})-{name_to_use}'

        self.images_by_id[img_id] = name_to_use
        self.names[name_key] = img_id
        return name_to_use


@dataclasses.dataclass
class PBR_Channel:
    """The concept of map and multiplication...
    Note that the default_values in Blender get overridden by the map
    while ThreeJS mutiplies the RGB value into the texture map
    """
    map: Union[bpy.types.Image, None] = None
    default_value: Union[float, Tuple, None] = None


class BlenderMaterialForExport:

    def __init__(self,
                 material: bpy.types.Material,
                 component_id: str = ""
                 ) -> None:
        from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ShaderData
    
        # valid name – this has to be the same as created inside the Blender addon
        self.pbr: PBR_ShaderData

        self.images: List[str] = []
        self.component_id: str = component_id
        self.blender_material_name: str = material.name
        self.material: bpy.types.Material = material

    @property
    def _component_id_prefix(self) -> str:
        if len(self.component_id) > 0:
            return f'{self.component_id}_'
        else:
            return ''
        
    @property
    def _component_id_suffix(self) -> str:
        if len(self.component_id) > 0:
            return f' ({self.component_id})'
        else:
            return ''
    
    @property
    def _valid_name(self):
        return utils_color.get_valid_name(self.blender_material_name)
    
    @property
    def material_id(self):
        return f'{self._component_id_prefix}{self._valid_name}'
    
    @property
    def label_en(self):
        # return f'{self._valid_name}{self._component_id_suffix}'
        return f'{self._valid_name}'
    
    @property
    def label_de(self):
        return self.label_en

    @property
    def used_nodes(self) -> Iterable:
        return utils_materials.get_all_used_nodes(self.material)

    @property
    def used_principled_bsdf_shader(self) -> bpy.types.ShaderNodeBsdfPrincipled:
        return utils_materials.get_principled_bsdf_node(self.material)
    
    @property
    def used_tex_nodes(self) -> list[bpy.types.ShaderNodeTexImage]:
        return utils_materials.get_used_texture_nodes(self.material)

