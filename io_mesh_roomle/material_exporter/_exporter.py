from __future__ import annotations
from typing import Iterable, List, Optional, Protocol, Tuple, Union

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ShaderData
import io_mesh_roomle.material_exporter.utils.materials as utils_materials
import dataclasses
import bpy

from io_mesh_roomle.material_exporter.utils import color as utils_color
from io_mesh_roomle.material_exporter._roomle_material_csv import Shading
from io_mesh_roomle import enums
from io_mesh_roomle.roomle_script import get_valid_name


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


@dataclasses.dataclass(kw_only=True)
class PBR_Channel_Base:
    """The concept of map and multiplication...
    Note that the default_values in Blender get overridden by the map
    while ThreeJS mutiplies the RGB value into the texture map
    """

    default_value: Union[float, Tuple, None] = None

    def default_value_rounded(
        self, precision: int = 2
    ) -> Union[None, float, list, tuple]:
        if self.default_value == None:
            return self.default_value
        if isinstance(self.default_value, (int, float)):
            return round(self.default_value, precision)
        if isinstance(self.default_value, (tuple, list)):
            return tuple([round(v, precision) for v in self.default_value])


@dataclasses.dataclass(kw_only=True)
class PBR_Channel(PBR_Channel_Base):
    map: Optional[bpy.types.Image] = None
    with_mm: float = 1
    height_mm: float = 1
    mapping: str = ""
    tileable: bool = True

    @property
    def zip_path(self) -> Union[None, str]:
        if self.map:
            return f"zip://{self.map}"
        else:
            return

    @property
    def texture_map_data_as_tuple(self) -> tuple:
        return (
            self.zip_path,
            self.mapping,
            self.with_mm,
            self.height_mm,
            self.tileable,
        )


def prec(value: Union[None, float], default: float):
    if value is None:
        return default
    return round(value, 2)


class BlenderMaterialForExport:
    """handle blender material and the corresponding roomle data"""

    def __init__(self, material: bpy.types.Material, component_id: str = "") -> None:

        self.images: List[str] = []
        self.component_id: str = component_id
        self.blender_material_name: str = material.name
        self.material: bpy.types.Material = material
        self.pbr: PBR_ShaderData = PBR_ShaderData(self.material)

    @property
    def _prefix_from_component_id(self) -> str:
        if len(self.component_id) > 0:
            return f"{self.component_id}_"
        else:
            return ""

    @property
    def _valid_name(self):
        return get_valid_name(self.blender_material_name)

    @property
    def material_id(self):
        return f"{self._prefix_from_component_id}{self._valid_name}"

    @property
    def label_en(self):
        # return f'{self._valid_name}{self._component_id_suffix}'
        return f"{self._valid_name}"

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

    @property
    def is_double_sided(self) -> bool:
        return not self.material.use_backface_culling

    @property
    def blend_mode(self) -> str:
        if self.material.blend_method in ("CLIP", "HASHED", "BLEND"):
            return "BLEND"
        else:
            return "OPAQUE"

    @property
    def csv_dict(self) -> dict:
        from io_mesh_roomle.material_exporter import MaterialCSVRow

        col = enums.MATERIALS_CSV_COLS

        shading = Shading()
        shading.alpha = prec(self.pbr.alpha.default_value, 1)
        shading.alphaMode = self.blend_mode
        shading.doubleSided = self.is_double_sided
        shading.roughness = prec(self.pbr.roughness.default_value, 0.5)
        shading.metallic = prec(self.pbr.metallic.default_value, 0)

        # TODO: handle the try blocks below more elegantly
        try:
            shading.basecolor.set(*self.pbr.diffuse.default_value)
        except:
            ...
        try:
            shading.sheenColor.set(*self.pbr.sheen.color[0:3])
            shading.sheenIntensity = self.pbr.sheen.sigma
        except:
            ...

        shading.transmission = prec(self.pbr.transmission.default_value, 0)
        shading.transmissionIOR = prec(self.pbr.ior.default_value, 1.5)
        shading.occlusion = prec(self.pbr.ao.default_value, 0)
        shading.emissiveColor.set(*self.pbr.emission.default_value)
        shading.emissiveIntensity = prec(self.pbr.emission_intensity.default_value, 0)

        row_handler = MaterialCSVRow()
        row_handler.set_field(col.SHADING, shading.to_json())
        row_handler.set_field(col.MATERIAL_ID, self.material_id)
        row_handler.set_field(col.LABEL_EN, self.label_en)
        row_handler.set_field(col.LABEL_DE, self.label_de)
        row_handler.set_field(col.ACTIVE, 1)

        row_handler.add_texture_field(*self.pbr.diffuse.texture_map_data_as_tuple)
        row_handler.add_texture_field(*self.pbr.normal.texture_map_data_as_tuple)
        row_handler.add_texture_field(*self.pbr.roughness.texture_map_data_as_tuple)
        row_handler.add_texture_field(*self.pbr.emission.texture_map_data_as_tuple)

        return row_handler.data_dict
