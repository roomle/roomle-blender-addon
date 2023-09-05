from __future__ import annotations  
from typing import List, TYPE_CHECKING

import bpy

if TYPE_CHECKING:
    from io_mesh_roomle.material_exporter._exporter import TextureNameManager, PBR_Channel

from io_mesh_roomle.material_exporter.socket_analyzer import pbr_channels


class PBR_ShaderData:
    """
    analyze a given material node network for known PBR node structures
    """
    def __init__(self, material: bpy.types.Material, principled_bsdf: bpy.types.ShaderNodeBsdfPrincipled , texture_name_manager: TextureNameManager) -> None:
        self.material = material
        self.texture_name_manager = texture_name_manager
        self.principled_bsdf = principled_bsdf


        # self.diffuse = PBR_Channel()      # ✅
        # self.alpha = PBR_Channel()        # ✅ 🕙 texture map handling
        # self.normal = PBR_Channel()       # ✅
        # self.roughness = PBR_Channel()    # ✅
        # self.metallic = PBR_Channel()     # ✅
        # self.transmission = PBR_Channel() # ✅
        # self.ior = PBR_Channel()          # ✅

        # # TODO: roomle support for emission.
        # # TODO: process ao maps (either bake inside the dap or find a way to blend it in threeJS)

        # self.ao = PBR_Channel()
        # self.emission = PBR_Channel()

        self.diffuse = pbr_channels.diffuse(self)
        self.normal = pbr_channels.normal(self)
        self.roughness = pbr_channels.roughness(self)
        self.metallic = pbr_channels.metallness(self)
        self.ior = pbr_channels.ior(self)
        self.transmission = pbr_channels.transmission(self)
        self.alpha = pbr_channels.alpha(self)
    
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
        from io_mesh_roomle.material_exporter._exporter import PBR_Channel
        try:
            res = [i for i in args if i is not None]
            assert len(res) == 1
            return res[0]
        except Exception as e:
            print(f'⛔️ {e}')
            return PBR_Channel()


class PBRChannelTester():
    pass