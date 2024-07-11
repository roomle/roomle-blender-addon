from __future__ import annotations
from dataclasses import dataclass
import bpy
from typing import Optional, Union

from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ChannelTester
from io_mesh_roomle.material_exporter.utils.materials import get_all_used_nodes

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
    def velvet_color(self) -> tuple:
        return tuple(self._velvet_node.inputs[0].default_value)

    @property
    def velvet_sigma(self):
        return self._velvet_node.inputs[1].default_value

    @property
    def velvet_normal(self):
        return self._velvet_node.inputs[2]

    def check_no_texture(self) -> Union[PBR_Channel, None]:
        if self._velvet_node is None:
            return
        return PBR_SheenChannel(color=self.velvet_color, sigma=self.velvet_sigma)
