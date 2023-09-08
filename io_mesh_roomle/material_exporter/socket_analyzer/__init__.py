from __future__ import annotations
import inspect
import logging  
from typing import Any, Iterable, List, TYPE_CHECKING, Union
from attr import dataclass

import bpy

from io_mesh_roomle.material_exporter.utils.materials import (
    get_principled_bsdf_node,
    get_socket_origin
    )

log = logging.getLogger('socket analyzer')
log.setLevel(logging.DEBUG)


if TYPE_CHECKING:
    from io_mesh_roomle.material_exporter._exporter import TextureNameManager, PBR_Channel


class ChannelBase:
    def __init__(self, material) -> None:
        pass

class CkeckError(Exception):
    pass

@dataclass
class PBR_DefaultValues():
    diffuse = (1.0,)*4
    alpha = 1.0 
    roughness = 1.0
    metallic = 1.0
    transmission = 1.0
    ior = 1.45

    # Not clear how to handle these
    normal = None
    ao = None
    emission = None


class PBR_ChannelTester():
    

    # The diffuse color has to be plain white in order to not tint the texture later in ThreeJS
    pbr_defaults: PBR_DefaultValues
    plain_white: tuple[float] = (1.0,)*3

    prefix = 'check_'
    def __init__(self, material: bpy.types.Material) -> None:
        self.material = material
        self.pbr_defaults = PBR_DefaultValues()

    @property
    def pbr_channel(self) -> PBR_Channel:
        return self._run_checks()


    def _run_checks(self):
        log.warning(f'running shader checks for {self.__class__.__name__}')
        methods = [meth for meth in dir(self) if meth.startswith(PBR_ChannelTester.prefix)]

        results = {}
        for check in methods:
            try:
                method = self.__getattribute__(check)
                pass
                results[check] = method()
            except CkeckError:
                pass

        return self.eliminate_none(results)
    
    @property
    def principled_bsdf(self) -> bpy.types.ShaderNodeBsdfPrincipled:
        return get_principled_bsdf_node(self.material)
    
    def p_bsdf_socket(self, slot:int) -> bpy.types.NodeSocket:
        return get_principled_bsdf_node(self.material).inputs[slot]
    
    def origin(self, socket: bpy.types.NodeSocket) -> Union[bpy.types.Node, None]:
        return get_socket_origin(self.material,socket)
    
    def assert_socket_is_linked(self, socket:bpy.types.NodeSocket) -> bool:
        if not socket.is_linked:
            raise CkeckError('socket is not linked')
        return True
    
    def assert_socket_is_not_linked(self, socket:bpy.types.NodeSocket) -> bool:
        if socket.is_linked:
            raise CkeckError('socket is linked')
        return True
        

    @staticmethod
    def eliminate_none(results: dict) -> PBR_Channel:
        from io_mesh_roomle.material_exporter._exporter import PBR_Channel
        values = []
        matched_checks = []
        try:
            for key,value in results.items():
                if value == None:
                    continue

                log.info(f'✅ check{key} matched with: {value}')
                values.append(value)
                matched_checks.append(key)
            if len(values) == 0:
                log.warning('no check matched')
                return PBR_Channel()
            assert len(values) == 1 , f'multiple matches: {matched_checks}'
            return values[0]
        except Exception as e:
            print(f'🛑 {e}')
            pass
            return PBR_Channel()

class PBR_ShaderData:
    """
    analyze a given material node network for known PBR node structures
    """
    def __init__(self, material: bpy.types.Material, texture_name_manager: TextureNameManager) -> None:
        from io_mesh_roomle.material_exporter._exporter import PBR_Channel
        from io_mesh_roomle.material_exporter.socket_analyzer import pbr_channels
        
        self.material = material
        self.texture_name_manager = texture_name_manager
        self.principled_bsdf: bpy.types.ShaderNodeBsdfPrincipled = get_principled_bsdf_node(material)

        log.warning(f'🎨 {material.name_full}')

        self.diffuse: PBR_Channel = pbr_channels.diffuse(self.material).pbr_channel      # ✅
        log.debug(f'📤 {self.diffuse.default_value}')
        self.alpha: PBR_Channel = pbr_channels.alpha(self)                               # ✅ 🕙 texture map handling
        self.normal: PBR_Channel = pbr_channels.normal(self)                             # ✅
        self.roughness: PBR_Channel = pbr_channels.roughness(self)                       # ✅
        self.metallic: PBR_Channel = pbr_channels.metallness(self.material).pbr_channel  # ✅
        self.transmission: PBR_Channel = pbr_channels.transmission(self)                 # ✅
        self.ior: PBR_Channel = pbr_channels.ior(self.material).pbr_channel              # ✅

        # # TODO: roomle support for emission.
        # # TODO: process ao maps (either bake inside the dap or find a way to blend it in threeJS)

        self.ao = PBR_Channel()
        self.emission = PBR_Channel()

    
    def socket_origin(self, socket: bpy.types.NodeSocket) -> Union[bpy.types.Node, None]:
        return get_socket_origin(self.material,socket)
    
    @property
    def all_pbr_channels(self) -> Iterable[PBR_Channel]:
        from io_mesh_roomle.material_exporter._exporter import PBR_Channel
        this_field_name = inspect.stack()[0][3]
        return [
            getattr(self, field)
            for field in dir(self)

            # check if the field is this function to avoid infinite calls
            if field != this_field_name
            
            and isinstance(getattr(self,field), PBR_Channel)
        ]



    @staticmethod
    def eliminate_none(*args) -> PBR_Channel:
        from io_mesh_roomle.material_exporter._exporter import PBR_Channel
        res = [i for i in args if i is not None]

        if len(res) == 1:
            return res[0]
        elif len(res) < 1:
            log.warning('found no known shader setup')
            return PBR_Channel()
        elif len(res) > 1:
            log.warning('the shader setup matched multiple checks')
            return PBR_Channel()


