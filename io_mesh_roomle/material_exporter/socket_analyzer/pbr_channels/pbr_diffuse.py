from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ChannelTester, CkeckError
from io_mesh_roomle.material_exporter.utils.materials import get_principled_bsdf_node, get_mix_shader_sockets, get_socket_origin

from io_mesh_roomle.material_exporter._exporter import PBR_Channel
from io_mesh_roomle.material_exporter._roomle_material_csv import TextureMapping
from io_mesh_roomle.material_exporter.utils.color import linear_to_srgb


import logging

log = logging.getLogger(__name__)


class diffuse(PBR_ChannelTester):
    def __init__(self, material: bpy.types.Material) -> None:
        super().__init__(material)
        self.socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[0]
        self.def_val = [linear_to_srgb(c)
                        for c in self.socket.default_value[0:3]]
        log.debug(f'🎨 {self.def_val}')


    def check_no_texture(self) -> Union[PBR_Channel, None]:
        if self.socket.is_linked:
            return

        return PBR_Channel(
            default_value=self.def_val
        )

    def check_directly_attached_image(self) -> Union[PBR_Channel, None]:
        n = self.origin(self.socket)
        if not isinstance(n, bpy.types.ShaderNodeTexImage):
            return
        w,h = self.image_dimensions(n)
        return PBR_Channel(
            map=n.image,
            with_mm=w,
            height_mm=h,
            mapping=TextureMapping.RGBA,
            default_value=self.pbr_defaults.diffuse
        )

    def check_indirectly_attached_image_3_3(self) -> Union[PBR_Channel, None]:
        self.assert_socket_is_linked(self.socket)

        n = self.origin(self.socket)

        if not isinstance(n, bpy.types.ShaderNodeMixRGB):
            return

        socket_a = n.inputs[1]
        n = self.origin(socket_a)

        if not isinstance(n, bpy.types.ShaderNodeTexImage):
            return

        return PBR_Channel(
            map=n.image,
            mapping=TextureMapping.RGBA,
            default_value=self.pbr_defaults.diffuse
        )

    def check_indirectly_attached_image(self) -> Union[PBR_Channel, None]:
        self.assert_socket_is_linked(self.socket)

        n = self.origin(self.socket)

        if not isinstance(n, bpy.types.ShaderNodeMix):
            return

        factor, a, b = get_mix_shader_sockets(n)

        if factor.is_linked:
            return None
        if not (factor.default_value == 0 or factor.default_value == 1):
            return None

        # TODO: assuming all vertex colors are white and have no effect on the texture

        tex_node = [ori for ori in (self.origin(a), self.origin(b)) if isinstance(
            ori, bpy.types.ShaderNodeTexImage)]

        if len(tex_node) != 1:
            return None

        n = tex_node[0]
        
        tex_node = [ori for ori in (a, b) if self.origin(ori) == None]

        if len(tex_node) != 1:
            return None

        c = tex_node[0]
        
        return PBR_Channel(
            map=n.image,
            mapping=TextureMapping.RGBA,
            default_value=tuple(c.default_value)[0:3]
        )

    def check_indirectly_attached_color(self) -> Union[PBR_Channel, None]:
        self.assert_socket_is_linked(self.socket)

        n = self.origin(self.socket)

        if not isinstance(n, bpy.types.ShaderNodeMix):
            return

        factor, a, b = get_mix_shader_sockets(n)
        n_a = self.origin(a)
        n_b = self.origin(b)

        if isinstance(n_b, bpy.types.ShaderNodeTexImage):
            return
        if isinstance(n_a, bpy.types.ShaderNodeTexImage):
            return

        n = self.origin(a)

        # TODO: handle more node setups
        return PBR_Channel(
            default_value=b.default_value  # [0:3]
        )
    
    def check_indirectly_attched_with_vertex_colors(self) -> Union[PBR_Channel, None]:
        """ignore vertex colors since they are not yet supported by the frontend"""

        self.assert_socket_is_linked(self.socket)

        n = self.origin(self.socket)

        if not isinstance(n, bpy.types.ShaderNodeMix):
            return

        factor, a, b = get_mix_shader_sockets(n)

        if factor.is_linked:
            return None



        tex_node = [ori for ori in (self.origin(a), self.origin(b)) if isinstance(
            ori, bpy.types.ShaderNodeTexImage)]
        pass

        vertex_colors = [ori for ori in (self.origin(a), self.origin(b)) if isinstance(
            ori, bpy.types.ShaderNodeVertexColor)]

        if len(tex_node) != 1:
            return None
        if len(vertex_colors) != 1:
            return None
        
        #! We ignore the vertex colors for now !!!

        n = tex_node[0]
        
        return PBR_Channel(
            map=n.image,
            mapping=TextureMapping.RGBA
        )
