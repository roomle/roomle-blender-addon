from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING
if TYPE_CHECKING:
    from io_mesh_roomle.material_exporter.socket_analyzer import PBR_Analyzer
from io_mesh_roomle.material_exporter._exporter import PBR_Channel


def metallness(analyzer: PBR_Analyzer) -> PBR_Channel:
    socket: bpy.types.NodeSocket = analyzer.principled_bsdf.inputs[6]
    def_val = socket.default_value

    def no_texture() -> Union[PBR_Channel, None]:
        if socket.is_linked:
            return

        return PBR_Channel(
            default_value=def_val
        )

    def orm() -> Union[PBR_Channel, None]:
        if not socket.is_linked:
            return

        separate_color_node = analyzer.socket_origin(socket)
        if not isinstance(separate_color_node, bpy.types.ShaderNodeSeparateColor):
            return

        image_node = analyzer.socket_origin(separate_color_node.inputs[0])

        if not isinstance(image_node, bpy.types.ShaderNodeTexImage):
            return

        return PBR_Channel(
            map=analyzer.texture_name_manager.get_name(image_node.image),
            default_value=def_val
        )

    return analyzer.eliminate_none(
        no_texture(),
        orm(),
    )
