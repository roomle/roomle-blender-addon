from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ChannelTester
from io_mesh_roomle.material_exporter._exporter import PBR_Channel

# TODO: RML-6682 all texture maps get multiplied with the value provided
# TODO: RML-6682 we could then translate a setup with muted maps to roomle script


class metallness(PBR_ChannelTester):
    def __init__(self, material: bpy.types.Material) -> None:
        super().__init__(material)
        self.socket = self.principled_bsdf_socket(6)
        self.def_val: float = self.socket.default_value #type: ignore

    def check_no_texture(self) -> Union[PBR_Channel, None]:
        if self.socket.is_linked:
            return

        return PBR_Channel(
            default_value=self.def_val
        )

    def check_orm(self) -> Union[PBR_Channel, None]:
        if not self.socket.is_linked:
            return
        
        pass

        separate_color_node = self.origin(self.socket)
        if not isinstance(separate_color_node, bpy.types.ShaderNodeSeparateColor):
            return

        image_node = self.origin(separate_color_node.inputs[0])

        if not isinstance(image_node, bpy.types.ShaderNodeTexImage):
            return

        return PBR_Channel(
            map=image_node.image,
            default_value=self.pbr_defaults.metallic
        )
    
    def check_directly_attached_image(self) -> Union[PBR_Channel, None]:
        if not self.socket.is_linked:
            return
        pass
        image_node = self.origin(self.socket)

        if not isinstance(image_node, bpy.types.ShaderNodeTexImage):
            return

        return PBR_Channel(
            map=image_node.image,   
            default_value=self.pbr_defaults.metallic
        )

