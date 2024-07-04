from __future__ import annotations
from dataclasses import dataclass
import bpy
from typing import Optional, Union, TYPE_CHECKING

from io_mesh_roomle.material_exporter.socket_analyzer import (
    PBR_ChannelTester,
    CkeckError,
)
from io_mesh_roomle.material_exporter.utils.materials import (
    get_all_used_nodes,
    get_principled_bsdf_node,
    get_mix_shader_sockets,
    get_socket_origin,
)

from io_mesh_roomle.material_exporter._exporter import PBR_Channel_Base
from io_mesh_roomle.material_exporter._roomle_material_csv import TextureMapping
from io_mesh_roomle.material_exporter.utils.color import linear_to_srgb


import logging

log = logging.getLogger(__name__)

@dataclass
class PBR_SheenChannel:
    color: tuple
    sigma: float
    normal: Optional[int] = None

class sheen(PBR_ChannelTester):
    def __init__(self, material: bpy.types.Material) -> None:
        super().__init__(material)
        self.socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[0]
        self.def_val = [linear_to_srgb(c) for c in self.socket.default_value[0:3]]
        log.debug(f"🎨 {self.def_val}")

    @property
    def _velvet_node(self) -> Optional[bpy.types.ShaderNodeBsdfPrincipled]:
        """all used texture nodes in material's node tree"""
        velvet_node = [
            node
            for node in get_all_used_nodes(self.material)
            if isinstance(node, bpy.types.ShaderNodeBsdfVelvet)
        ]
        if len(velvet_node) != 1:
            return None
        return velvet_node[0]

    @property
    def velvet_color(self):
        return tuple(self._velvet_node.inputs[0].default_value)

    @property
    def velvet_sigma(self):
        return self._velvet_node.inputs[1].default_value

    @property
    def velvet_normal(self):
        return self._velvet_node.inputs[2]

    def check_no_texture(self) -> Union[PBR_Channel, None]:


        x = self._velvet_node
        if x is None:
            return None



        return PBR_SheenChannel(
            color=self.velvet_color,
            sigma=self.velvet_sigma
        )

    # def check_directly_attached_image(self) -> Union[PBR_Channel, None]:
    #     n = self.origin(self.socket)
    #     if not isinstance(n, bpy.types.ShaderNodeTexImage):
    #         return
    #     w,h = self.image_dimensions(n)
    #     return PBR_Channel(
    #         map=n.image,
    #         with_mm=w,
    #         height_mm=h,
    #         mapping=TextureMapping.RGBA,
    #         default_value=self.pbr_defaults.diffuse
    #     )

    # def check_indirectly_attached_image_3_3(self) -> Union[PBR_Channel, None]:
    #     self.assert_socket_is_linked(self.socket)

    #     n = self.origin(self.socket)

    #     if not isinstance(n, bpy.types.ShaderNodeMixRGB):
    #         return

    #     socket_a = n.inputs[1]
    #     n = self.origin(socket_a)

    #     if not isinstance(n, bpy.types.ShaderNodeTexImage):
    #         return

    #     return PBR_Channel(
    #         map=n.image,
    #         mapping=TextureMapping.RGBA,
    #         default_value=self.pbr_defaults.diffuse
    #     )

    # def check_indirectly_attached_image(self) -> Union[PBR_Channel, None]:
    #     self.assert_socket_is_linked(self.socket)

    #     n = self.origin(self.socket)

    #     if not isinstance(n, bpy.types.ShaderNodeMix):
    #         return

    #     factor, a, b = get_mix_shader_sockets(n)

    #     if factor.is_linked:
    #         return None
    #     if not (factor.default_value == 0 or factor.default_value == 1):
    #         return None

    #     # TODO: assuming all vertex colors are white and have no effect on the texture

    #     tex_node = [ori for ori in (self.origin(a), self.origin(b)) if isinstance(
    #         ori, bpy.types.ShaderNodeTexImage)]

    #     if len(tex_node) != 1:
    #         return None

    #     n = tex_node[0]

    #     tex_node = [ori for ori in (a, b) if self.origin(ori) == None]

    #     if len(tex_node) != 1:
    #         return None

    #     c = tex_node[0]

    #     return PBR_Channel(
    #         map=n.image,
    #         mapping=TextureMapping.RGBA,
    #         default_value=tuple(c.default_value)[0:3]
    #     )

    # def check_indirectly_attached_color(self) -> Union[PBR_Channel, None]:
    #     self.assert_socket_is_linked(self.socket)

    #     n = self.origin(self.socket)

    #     if not isinstance(n, bpy.types.ShaderNodeMix):
    #         return

    #     factor, a, b = get_mix_shader_sockets(n)
    #     n_a = self.origin(a)
    #     n_b = self.origin(b)

    #     if isinstance(n_b, bpy.types.ShaderNodeTexImage):
    #         return
    #     if isinstance(n_a, bpy.types.ShaderNodeTexImage):
    #         return

    #     n = self.origin(a)

    #     # TODO: handle more node setups
    #     return PBR_Channel(
    #         default_value=b.default_value  # [0:3]
    #     )
