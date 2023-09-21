from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ChannelTester
from io_mesh_roomle.material_exporter._exporter import PBR_Channel


class roughness(PBR_ChannelTester):
    def __init__(self, material: Material) -> None:
        super().__init__(material)
        self.socket = self.principled_bsdf_socket(9)
        self.def_value = self.socket.default_value

    def check_no_texture(self) -> Union[PBR_Channel, None]:
        socket = self.socket
        if socket.is_linked:
            return

        return PBR_Channel(
            default_value=self.def_value
        )

    def check_orm(self) -> Union[PBR_Channel, None]:
        socket = self.socket
        if not socket.is_linked:
            return

        separate_color_node = self.origin(socket)
        if not isinstance(separate_color_node, bpy.types.ShaderNodeSeparateColor):
            return

        image_node = self.origin(separate_color_node.inputs[0])

        if not isinstance(image_node, bpy.types.ShaderNodeTexImage):
            return

        return PBR_Channel(
            map=image_node.image,
            default_value=self.def_value
        )
