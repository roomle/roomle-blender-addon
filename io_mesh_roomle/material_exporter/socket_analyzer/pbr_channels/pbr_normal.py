from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ChannelTester
from io_mesh_roomle.material_exporter._exporter import PBR_Channel


class normal(PBR_ChannelTester):
    def __init__(self, material: Material) -> None:
        super().__init__(material)
        self.socket= self.principled_bsdf_socket(22)
        
    def check_standard_normal(self) -> Union[PBR_Channel, None]:
        socket = self.socket
        if not socket.is_linked:
            return
        normal_map_node = self.origin(socket)

        if not isinstance(normal_map_node, bpy.types.ShaderNodeNormalMap):
            pass

        image_texture = self.origin(normal_map_node.inputs[1])

        if not isinstance(image_texture, bpy.types.ShaderNodeTexImage):
            pass
        try:
            return PBR_Channel(
                map=image_texture.image
            )
        except Exception as e:
            pass
