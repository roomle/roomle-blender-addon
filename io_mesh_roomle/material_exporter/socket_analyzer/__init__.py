from typing import List

import bpy

from io_mesh_roomle.material_exporter._exporter import (PBR_Channel,
                                                        PBR_ShaderData,
                                                        TextureNameManager)
from io_mesh_roomle.material_exporter.socket_analyzer.pbr_channels import alpha
from io_mesh_roomle.material_exporter.socket_analyzer.pbr_channels import diffuse
from io_mesh_roomle.material_exporter.socket_analyzer.pbr_channels import ior
from io_mesh_roomle.material_exporter.socket_analyzer.pbr_channels import metallness
from io_mesh_roomle.material_exporter.socket_analyzer.pbr_channels import normal
from io_mesh_roomle.material_exporter.socket_analyzer.pbr_channels import roughness
from io_mesh_roomle.material_exporter.socket_analyzer.pbr_channels import transmission


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
        data.diffuse = diffuse(self)
        data.normal = normal(self)
        data.roughness = roughness(self)
        data.metallic = metallness(self)
        data.ior = ior(self)
        data.transmission = transmission(self)
        data.alpha = alpha(self)

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
