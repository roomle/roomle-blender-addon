from dataclasses import dataclass
from email.mime import image
from pathlib import Path
import re
from shutil import copy
from typing import List, Tuple, Union
import bpy
from ._roomle_material_csv import (
    RoomleMaterialsCsv,
    MaterialDefinition,
)
import math
from ._file_formats import SUPPORTED_TEXTURE_FILE_FORMATS

def linear_to_srgb(c:float) -> float:
    """convert linear color value to srgb

    Args:
        c (float): one of the color values (rgb)

    Returns:
        float: srgb representation
    """
    if c < 0.0031308:
        srgb = 0.0 if c < 0.0 else c * 12.92
    else:
        srgb = 1.055 * math.pow(c, 1.0 / 2.4) - 0.055
    return max(min(int(srgb * 255 + 0.5), 255), 0) / 255

def get_valid_name(name: str) -> str:
    """make a filename valid – the same as inside the roomle blender extension

    Args:
        name (str): the string to start from

    Returns:
        str: valid filename
    """
    return re.sub('[^0-9a-zA-Z:_]+', '', name)


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


class PBR_Analyzer:
    """
    analyze a given material node network for known PBR node structures
    """
    principled_bsdf: bpy.types.ShaderNodeBsdfPrincipled
    material: bpy.types.Material
    pbr_data: PBR_ShaderData

    def __init__(self, material: bpy.types.Material, used_nodes: List[bpy.types.Node], texture_name_manager: TextureNameManager) -> None:
        self.material = material
        self.texture_name_manager = texture_name_manager

        # find the principledBSDF node
        self.principled_bsdf = [node for node in used_nodes if isinstance(
            node, bpy.types.ShaderNodeBsdfPrincipled)][0]

        self.pbr_data = self._run()

    def _run(self) -> PBR_ShaderData:
        """run the analysis on given sockets

        Returns:
            PBR_ShaderData: _description_
        """
        data = PBR_ShaderData()
        data.diffuse = self.diffuse()
        data.normal = self.normal()
        data.roughness = self.roughness()
        data.metallic = self.metallness()
        data.ior = self.ior()
        data.transmission = self.transmission()
        data.alpha = self.alpha()

        return data

    def socket_origin(self, socket: bpy.types.NodeSocket) -> bpy.types.Node:
        """find the attached node to a given socket
        the socket is expected to be single input

        Args:
            socket (bpy.types.NodeSocket): given socket

        Returns:
            bpy.types.Node: the connected node
        """
        try:
            links = self.material.node_tree.links

            assert not socket.is_multi_input
            assert socket.is_linked

            return [e.from_node for e in links if e.to_socket == socket][0]
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def eliminate_none(*args) -> PBR_Channel:
        try:
            res = [i for i in args if i is not None]
            assert len(res) == 1
            return res[0]
        except Exception as e:
            print(e)
            return PBR_Channel()

    # =========================== SOCKET ANALYZER ========================

    def diffuse(self) -> PBR_Channel:
        socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[0]
        def_val = [linear_to_srgb(c) for c in socket.default_value[0:3]]
        origin = self.socket_origin

        def no_texture() -> Union[PBR_Channel, None]:
            if socket.is_linked:
                return

            return PBR_Channel(
                default_value=def_val
            )

        def directly_attached_image() -> Union[PBR_Channel, None]:
            n = origin(socket)
            if not isinstance(n, bpy.types.ShaderNodeTexImage):
                return
            return PBR_Channel(
                map=self.texture_name_manager.get_name(n.image),
                default_value=def_val
            )

        def indirectly_attached_image() -> Union[PBR_Channel, None]:
            if not socket.is_linked:
                return

            n = origin(socket)

            if not isinstance(n, bpy.types.ShaderNodeMixRGB):
                return

            socket_a = n.inputs[1]
            n = origin(socket_a)

            if not isinstance(n, bpy.types.ShaderNodeTexImage):
                return

            return PBR_Channel(
                map=self.texture_name_manager.get_name(n.image),
                default_value=def_val
            )

        def indirectly_attached_color() -> Union[PBR_Channel, None]:
            if not socket.is_linked:
                return

            n = origin(socket)

            if not isinstance(n, bpy.types.ShaderNodeMixRGB):
                return

            socket_a = n.inputs[1]
            n_b = origin(socket_a)

            if isinstance(n_b, bpy.types.ShaderNodeTexImage):
                return

            socket_b = n.inputs[2]
            return PBR_Channel(
                default_value=socket_b.default_value[0:3]
            )

        return self.eliminate_none(
            no_texture(),
            directly_attached_image(),
            indirectly_attached_image(),
            indirectly_attached_color(),
        )

    def normal(self) -> PBR_Channel:
        socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[22]

        def standard_normal() -> Union[PBR_Channel, None]:
            if not socket.is_linked:
                return
            normal_map_node = self.socket_origin(socket)

            if not isinstance(normal_map_node, bpy.types.ShaderNodeNormalMap):
                pass

            image_texture = self.socket_origin(normal_map_node.inputs[1])

            if not isinstance(image_texture, bpy.types.ShaderNodeTexImage):
                pass
            try:
                return PBR_Channel(
                    map=self.texture_name_manager.get_name(image_texture.image)
                )
            except Exception as e:
                pass

        return self.eliminate_none(
            standard_normal(),
        )

    def roughness(self) -> PBR_Channel:
        socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[9]
        def_value = socket.default_value

        def no_texture() -> Union[PBR_Channel, None]:
            if socket.is_linked:
                return

            return PBR_Channel(
                default_value=def_value
            )

        def orm() -> Union[PBR_Channel, None]:
            if not socket.is_linked:
                return

            separate_color_node = self.socket_origin(socket)
            if not isinstance(separate_color_node, bpy.types.ShaderNodeSeparateColor):
                return

            image_node = self.socket_origin(separate_color_node.inputs[0])

            if not isinstance(image_node, bpy.types.ShaderNodeTexImage):
                return

            return PBR_Channel(
                map=self.texture_name_manager.get_name(image_node.image),
                default_value=def_value
            )

        return self.eliminate_none(
            no_texture(),
            orm(),
        )

    def metallness(self) -> PBR_Channel:
        socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[6]
        def_val = socket.default_value

        def no_texture() -> Union[PBR_Channel, None]:
            if socket.is_linked:
                return

            return PBR_Channel(
                default_value=def_val
            )

        def orm() -> Union[PBR_Channel, None]:
            if not socket.is_linked:
                return

            separate_color_node = self.socket_origin(socket)
            if not isinstance(separate_color_node, bpy.types.ShaderNodeSeparateColor):
                return

            image_node = self.socket_origin(separate_color_node.inputs[0])

            if not isinstance(image_node, bpy.types.ShaderNodeTexImage):
                return

            return PBR_Channel(
                map=self.texture_name_manager.get_name(image_node.image),
                default_value=def_val
            )

        return self.eliminate_none(
            no_texture(),
            orm(),
        )

    def ior(self) -> PBR_Channel:
        socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[16]
        def_val = socket.default_value

        def no_texture() -> Union[PBR_Channel, None]:
            if socket.is_linked:
                return
            return PBR_Channel(
                default_value=def_val
            )

        return self.eliminate_none(
            no_texture()
        )

    def transmission(self) -> PBR_Channel:
        socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[17]
        def_val = socket.default_value

        def no_texture() -> Union[PBR_Channel, None]:
            if socket.is_linked:
                return
            return PBR_Channel(
                default_value=def_val
            )

        return self.eliminate_none(
            no_texture()
        )

    def alpha(self) -> PBR_Channel:
        socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[21]
        def_val = socket.default_value

        def no_texture() -> Union[PBR_Channel, None]:
            if socket.is_linked:
                return
            return PBR_Channel(
                default_value=def_val
            )

        return self.eliminate_none(
            no_texture()
            # TODO: image alpha?
        )

    # ========================= SOCKET ANALYZER END ======================


class BlenderMaterialForExport:
    name: str
    material: bpy.types.Material
    used_nodes: List = []
    images: List[str] = []
    pbr: PBR_ShaderData

    def __init__(self, material: bpy.types.Material, out_path: Path, texture_name_manager: TextureNameManager) -> None:

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

        def sinn(value: Union[str, None]):
            if value is None:
                return ''
            return 'zip://' + value.rsplit('/')[-1]

        def prec(value: Union[float, None], default: float):
            if value is None:
                return default
            return round(value, 2)

        pbr = data.pbr
        md = MaterialDefinition()

        md.material_id = data.name
        md.label_en = data.name
        md.label_de = data.name

        md.shading.alpha = prec(pbr.alpha.default_value, 1)                # type: ignore
        md.shading.roughness = prec(pbr.roughness.default_value, 0.5)      # type: ignore
        md.shading.metallic = prec(pbr.metallic.default_value, 0)          # type: ignore
        md.shading.basecolor.set(*pbr.diffuse.default_value)               # type: ignore

        md.shading.transmission = prec(pbr.transmission.default_value, 0)  # type: ignore
        md.shading.transmissionIOR = prec(pbr.ior.default_value, 1.5)      # type: ignore

        md.diffuse_map.image = sinn(pbr.diffuse.map)
        md.diffuse_map.mapping = "RGB"

        md.normal_map.image = sinn(pbr.normal.map)
        md.normal_map.mapping = "XYZ"

        md.orm_map.image = sinn(pbr.roughness.map)
        md.orm_map.mapping = "ORM"
        return md
