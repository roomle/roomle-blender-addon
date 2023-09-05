from dataclasses import dataclass
from email.mime import image
from pathlib import Path
from shutil import copy
from typing import List, Protocol, Tuple, Union
import bpy



from io_mesh_roomle.material_exporter.utils import get_valid_name
from ..enums import SUPPORTED_TEXTURE_FILE_FORMATS


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

    def validate_name(self, image: ObjectToRegister) -> str:
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



@dataclass
class PBR_Channel:
    """The concept of map and multiplocation
    Note that the default_values in Blender get overridden by the map
    """
    map: Union[str, None] = None
    default_value: Union[float, Tuple, None] = None


class PBR_ShaderData:
    def __init__(self) -> None:
        self.diffuse = PBR_Channel()      # ✅
        self.alpha = PBR_Channel()        # ✅ 🕙 texture map handling
        self.normal = PBR_Channel()       # ✅
        self.roughness = PBR_Channel()    # ✅
        self.metallic = PBR_Channel()     # ✅
        self.transmission = PBR_Channel() # ✅
        self.ior = PBR_Channel()          # ✅

        # TODO: roomle support for emission.
        # TODO: process ao maps (either bake inside the dap or find a way to blend it in threeJS)

        self.ao = PBR_Channel()
        self.emission = PBR_Channel()




class BlenderMaterialForExport:

    def __init__(self,
                 material: bpy.types.Material
                 ) -> None:
        from io_mesh_roomle.material_exporter.socket_analyzer import PBR_Analyzer
    
        # valid name – this has to be the same as created inside the Blender addon
        self.pbr: PBR_ShaderData

        self.images: List[str] = []
        self.name: str = get_valid_name(material.name)
        self.material: bpy.types.Material = material


    @property
    def used_nodes(self) -> List:
        """find only the used nodes in material's node tree.
        staring at the output node and walking all nodes backwards
        """
        material = self.material
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

    @property
    def used_principled_bsdf_shader(self) -> bpy.types.ShaderNodeBsdfPrincipled:
        princilpled_nodes = [node for node in self.used_nodes if isinstance(node, bpy.types.ShaderNodeBsdfPrincipled)]
        assert len(princilpled_nodes) > 0, 'no principled bsdf node found'
        assert len(princilpled_nodes) < 2, 'multiple principled bsdf nodes found'
        return princilpled_nodes[0]
    
    @property
    def used_tex_nodes(self) -> list[bpy.types.ShaderNodeTexImage]:
        """all used texture nodes in material's node tree"""
        return [node for node in self.used_nodes if isinstance(node, bpy.types.ShaderNodeTexImage)]

