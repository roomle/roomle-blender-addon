from __future__ import annotations
import bpy
from typing import Union

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ChannelTester
from io_mesh_roomle.material_exporter._exporter import PBR_Channel



class alpha(PBR_ChannelTester):
    # TODO: image alpha?
    def __init__(self, material: bpy.types.Material) -> None:
        super().__init__(material)
        self.socket = self.principled_bsdf_socket(21)
        self.def_val = self.socket.default_value

    def check_no_texture(self) -> Union[PBR_Channel, None]:
        if self.socket.is_linked:
            return
        return PBR_Channel(
            default_value=self.def_val
        )
