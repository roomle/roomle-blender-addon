from __future__ import annotations
import bpy
from typing import Union, TYPE_CHECKING
if TYPE_CHECKING:
    from io_mesh_roomle.material_exporter.socket_analyzer import PBR_ShaderData
from io_mesh_roomle.material_exporter._exporter import PBR_Channel


def alpha(self: PBR_ShaderData) -> PBR_Channel:
    socket: bpy.types.NodeSocket = self.principled_bsdf.inputs[21]
    def_val = socket.default_value

    def no_texture() -> Union[PBR_Channel, None]:
        if socket.is_linked:
            return
        return PBR_Channel(
            default_value=def_val
        )

    return self.eliminate_none(
        no_texture()
        # TODO: image alpha?
    )
