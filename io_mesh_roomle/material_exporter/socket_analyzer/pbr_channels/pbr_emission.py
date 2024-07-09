from __future__ import annotations
from dataclasses import dataclass
import bpy
from typing import Union, TYPE_CHECKING

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ChannelTester
from io_mesh_roomle.material_exporter._roomle_material_csv import TextureMapping
from io_mesh_roomle.material_exporter._exporter import PBR_Channel, PBR_Channel_Base
from io_mesh_roomle.material_exporter.utils.color import linear_to_srgb


class emission_color(PBR_ChannelTester):
    def __init__(self, material: bpy.types.Material) -> None:
        super().__init__(material)
        self.socket:bpy.types.NodeSocketColor = self.principled_bsdf_socket(19)  # color or image

    @property
    def def_val(self):
        return [linear_to_srgb(c) for c in self.socket.default_value[0:3]]

    def check_not_connected(self):
        if not self.socket.is_linked:
            return PBR_Channel(default_value=self.def_val)
    
    def check_image_map_attached(self):
        n = self.origin(self.socket)
        if not isinstance(n, bpy.types.ShaderNodeTexImage):
            return
        
        w,h = self.image_dimensions(n)

        return PBR_Channel(
            map=n.image,
            with_mm=w,
            height_mm=h,
            mapping=TextureMapping.EMRGB,
            default_value=self.pbr_defaults.diffuse
        )
    


class emission_intensity(PBR_ChannelTester):
    def __init__(self, material: bpy.types.Material) -> None:
        super().__init__(material)
        self.socket = self.principled_bsdf_socket(20)  # strength
        self.def_val = self.socket.default_value

    def check_not_connected(self):
        if not self.socket.is_linked:
            return PBR_Channel(default_value=self.def_val)
