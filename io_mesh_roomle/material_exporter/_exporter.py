from dataclasses import dataclass
from email.mime import image
from pathlib import Path
from shutil import copy
from typing import List, Tuple, Union
import bpy



from io_mesh_roomle.material_exporter.utils import get_valid_name
from ._roomle_material_csv import (
    RoomleMaterialsCsv,
    MaterialDefinition,
)
from ..enums import SUPPORTED_TEXTURE_FILE_FORMATS


class TextureNameManager:
    """keeps track of image file name used to avoid overwriting of texture files using the same name
    """

    def __init__(self) -> None:
        # imagenode_id : filename
        self.images_by_id = {}

        # filename : imagenode_id
        self.names = {}

    def validate_name(self, image: bpy.types.Image) -> str:
        """returns a valid name by checking the requested name against already used ones.
        also registers the name in the class dictionaries

        Args:
            image (bpy.types.Image): the image node to check
            name_to_use (str): the desired name

        Returns:
            str: a valid filename without the path
        """

        file_format = image.file_format
        if not file_format in SUPPORTED_TEXTURE_FILE_FORMATS:
            raise Exception(f'unsupported texture type {file_format}')

        suffix = SUPPORTED_TEXTURE_FILE_FORMATS[image.file_format]
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

    def get_name(self, image: bpy.types.Image) -> str:
        """get the file name for a given image

        Args:
            image (bpy.types.Image): the image object to get the name for

        Returns:
            str: the name to use
        """
        img_id = id(image)
        assert img_id in self.images_by_id.keys()
        return self.images_by_id[id(image)]


@dataclass
class PBR_Channel:
    """The concept of map and multiplocation
    Note that the default_values in Blender get overridden by the map
    """
    map: Union[str, None] = None
    default_value: Union[float, Tuple, None] = None


class PBR_ShaderData:
    diffuse: PBR_Channel          # ✅

    # TODO: alpha channel does work in roomle as expected
    alpha: PBR_Channel            # ✅ 🕙 texture map handling
    normal: PBR_Channel           # ✅
    roughness: PBR_Channel        # ✅
    metallic: PBR_Channel         # ✅
    transmission: PBR_Channel     # ✅
    ior: PBR_Channel              # ✅

    # TODO: roomle support for emission.
    # TODO: process ao maps (either bake inside the dap or find a way to blend it in threeJS)
    ao: PBR_Channel               #
    emission: PBR_Channel         #

    def __init__(self) -> None:
        self.diffuse = PBR_Channel()
        self.alpha = PBR_Channel()
        self.normal = PBR_Channel()
        self.roughness = PBR_Channel()
        self.metallic = PBR_Channel()
        self.transmission = PBR_Channel()
        self.ior = PBR_Channel()
        self.ao = PBR_Channel()
        self.emission = PBR_Channel()




class BlenderMaterialForExport:
    name: str
    material: bpy.types.Material
    used_nodes: List = []
    images: List[str] = []
    pbr: PBR_ShaderData

    def __init__(self, material: bpy.types.Material, out_path: Path, texture_name_manager: TextureNameManager) -> None:
        from io_mesh_roomle.material_exporter.socket_analyzer import PBR_Analyzer
        
        # valid name – this has to be the same as created inside the Blender addon
        self.name = get_valid_name(material.name)

        self.out_path = out_path
        self.material = material
        self.used_nodes = self.find_used_nodes(self.material)
        self.unpack_images(texture_name_manager)
        self.pbr = PBR_Analyzer(
            self.material, self.used_nodes, texture_name_manager).pbr_data
        pass

    @staticmethod
    def find_used_nodes(material: bpy.types.Material) -> List:
        """find only the used nodes in a material definition by starting
        at the output node and walking all nodes backwards

        Args:
            material (bpy.types.Material): _description_
        """
        def find_incoming_nodes(base_node, links) -> List:
            """recursive sub function"""
            connected_nodes = [
                edge.from_node for edge in links if edge.to_node == base_node]
            for node in connected_nodes:
                connected_nodes += find_incoming_nodes(node, links)
            return connected_nodes

        # TODO: find the active material output node if multiple are given

        # Find the output node of the material as the starting point
        material_output = [node for node in material.node_tree.nodes if isinstance(
            node, bpy.types.ShaderNodeOutputMaterial)]

        # We only expect one output node for an imported glb
        assert len(material_output) == 1

        # list of used nodes in the definition, passed through a `set` to avoid duplicates
        used_nodes = list(set(
            material_output +
            find_incoming_nodes(
                base_node=material_output[0],
                links=material.node_tree.links
            )
        ))
        return used_nodes

    def unpack_images(self, texture_name_manager: TextureNameManager):
        """unpack the images of all used `ShaderNodeTexImage` and prpend the material name
        """

        # TODO: manage external images with same name. rather use `node.image.name` as file name

        for node in [node for node in self.used_nodes if isinstance(node, bpy.types.ShaderNodeTexImage)]:
            name = texture_name_manager.validate_name(node.image)
            node.image.save(filepath=str(self.out_path / 'materials' / name))


class RoomleMaterialExporter:

    def __init__(self, objects_to_export, out_path: Path) -> None:
        self.out_folder: Path = out_path
        self.csv_exporter = RoomleMaterialsCsv()
        self.material_exports: List[BlenderMaterialForExport] = []
        self.texture_name_manager = TextureNameManager()

        for mat in bpy.data.materials:
            if mat.users < 1:
                continue
            if mat.node_tree == None:
                continue
            objs_using_mat = [obj for obj in objects_to_export
                              if obj.type == 'MESH' and
                              mat.name in obj.data.materials]
            if len(objs_using_mat) < 1:
                continue
            self.material_exports.append(BlenderMaterialForExport(
                mat, self.out_folder, self.texture_name_manager))

        for mat in self.material_exports:
            self.csv_exporter.add_material_definition(
                self.pbr_2_material_definition(mat)
            )
        self.csv_exporter.write(out_path / 'materials/materials.csv')

    @staticmethod
    def pbr_2_material_definition(data: BlenderMaterialForExport) -> MaterialDefinition:

        def zip_path(value: Union[str, None]):
            if value is None:
                return ''
            # return 'zip://' + value.rsplit('/')[-1]
            return value.replace('//textures/', 'zip://')

        def prec(value: Union[float, None], default: float):
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


        md.shading.basecolor.set(
                pbr.diffuse.default_value)               # type: ignore

        md.shading.transmission = prec(
            pbr.transmission.default_value, 0)  # type: ignore
        md.shading.transmissionIOR = prec(
            pbr.ior.default_value, 1.5)      # type: ignore

        # md.diffuse_map.image = zip_path(pbr.diffuse.map)
        md.diffuse_map.image = f'zip://{pbr.diffuse.map}'
        md.diffuse_map.mapping = "RGB" if zip_path(
            pbr.diffuse.map) != '' else ''

        md.normal_map.image = zip_path(pbr.normal.map)
        md.normal_map.mapping = "XYZ" if zip_path(pbr.normal.map) != '' else ''

        md.orm_map.image = zip_path(pbr.roughness.map)
        md.orm_map.mapping = "ORM" if zip_path(pbr.roughness.map) != '' else ''
        return md


