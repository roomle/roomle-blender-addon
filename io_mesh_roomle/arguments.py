import dataclasses
from pathlib import Path
import mashumaro

@dataclasses.dataclass
class addon_arguments(mashumaro.DataClassDictMixin):
    filepath: Path
    catalog_id: str
    use_selection: bool
    export_normals: bool
    export_materials: bool
    apply_rotations: bool
    use_corto: bool
    mesh_export_option: str
    uv_float_precision: int
    normal_float_precision: int
    component_id: str
    debug: bool

    @property
    def component_tag(self) -> str:
        return self.component_id
    
    @property
    def component_tag_label_en(self) -> str:
        return self.component_id.replace('_',' ')
    
    @property
    def catalog_root_tag(self) -> str:
        return f'{self.catalog_id}_root'



