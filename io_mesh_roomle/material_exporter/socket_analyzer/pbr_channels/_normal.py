from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING
if TYPE_CHECKING:
    from io_mesh_roomle.material_exporter.socket_analyzer import PBR_Analyzer
from io_mesh_roomle.material_exporter._exporter import PBR_Channel


def normal(analyzer: PBR_Analyzer) -> PBR_Channel:
    socket: bpy.types.NodeSocket = analyzer.principled_bsdf.inputs[22]

    def standard_normal() -> Union[PBR_Channel, None]:
        if not socket.is_linked:
            return
        normal_map_node = analyzer.socket_origin(socket)

        if not isinstance(normal_map_node, bpy.types.ShaderNodeNormalMap):
            pass

        image_texture = analyzer.socket_origin(normal_map_node.inputs[1])

        if not isinstance(image_texture, bpy.types.ShaderNodeTexImage):
            pass
        try:
            return PBR_Channel(
                map=analyzer.texture_name_manager.get_name(image_texture.image)
            )
        except Exception as e:
            pass

    return analyzer.eliminate_none(
        standard_normal(),
    )
