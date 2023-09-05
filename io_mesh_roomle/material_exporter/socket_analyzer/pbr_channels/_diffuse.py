from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING
if TYPE_CHECKING:
    from io_mesh_roomle.material_exporter.socket_analyzer import PBR_Analyzer

from io_mesh_roomle.material_exporter._exporter import PBR_Channel
from io_mesh_roomle.material_exporter.utils import linear_to_srgb



class MaterialNodeAnalyzer():
    def __init__(self) -> None:
        pass
    


def diffuse(analyzer: PBR_Analyzer) -> PBR_Channel:
    socket: bpy.types.NodeSocket = analyzer.principled_bsdf.inputs[0]
    def_val = [linear_to_srgb(c) for c in socket.default_value[0:3]]
    origin = analyzer.socket_origin

    def no_texture() -> Union[PBR_Channel, None]:
        if socket.is_linked:
            return

        return PBR_Channel(
            default_value=def_val
        )

    def directly_attached_image() -> Union[PBR_Channel, None]:
        n = origin(socket)
        if not isinstance(n, bpy.types.ShaderNodeTexImage):
            return
        return PBR_Channel(
            map=analyzer.texture_name_manager.validate_name(n.image),
            default_value=def_val
        )
    def indirectly_attached_image_3_3() -> Union[PBR_Channel, None]:
        if not socket.is_linked:
            return

        n = origin(socket)

        if not isinstance(n, bpy.types.ShaderNodeMixRGB):
            return

        socket_a = n.inputs[1]
        n = origin(socket_a)

        if not isinstance(n, bpy.types.ShaderNodeTexImage):
            return

        return PBR_Channel(
            map=self.texture_name_manager.get_name(n.image),
            default_value=def_val
        )
    def indirectly_attached_image() -> Union[PBR_Channel, None]:
        if not socket.is_linked:
            return

        n = origin(socket)

        if not isinstance(n, bpy.types.ShaderNodeMix):
            return

        active_inputs = [i for i in n.inputs if i.enabled]

        factor = [i for i in active_inputs if "Factor" in i.identifier][0]

        # get active inputs for slot A and B
        a = [i for i in active_inputs if "A" in i.identifier][0]
        b = [i for i in active_inputs if "B" in i.identifier][0]

        if factor.is_linked:
            return None
        if not (factor.default_value == 0 or factor.default_value == 1):
            return None

        # TODO: assuming all vertex colors are whit and hav eno effect on the texture

        tex_node = [ori for ori in (origin(a), origin(b)) if isinstance(
            ori, bpy.types.ShaderNodeTexImage)]

        if len(tex_node) != 1:
            return None

        n = tex_node[0]
        # i_name = analyzer.texture_name_manager.get_name(n.image)
        i_name = analyzer.texture_name_manager.validate_name(n.image)
        return PBR_Channel(
            map=i_name,
            default_value=def_val
        )

    def indirectly_attached_color() -> Union[PBR_Channel, None]:
        if not socket.is_linked:
            return

        n = origin(socket)

        if not isinstance(n, bpy.types.ShaderNodeMix):
            return

        socket_a = n.inputs[1]
        n_b = origin(socket_a)

        if isinstance(n_b, bpy.types.ShaderNodeTexImage):
            return

        socket_b = n.inputs[2]
        return PBR_Channel(
            default_value=socket_b.default_value  # [0:3]
        )

    return analyzer.eliminate_none(
        no_texture(),
        directly_attached_image(),
        indirectly_attached_image(),
        # indirectly_attached_image_3_3(),
        # TODO: mix shader 
        # indirectly_attached_color(), 
    )
