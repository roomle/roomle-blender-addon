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
    
    @property
    def component_ext_id(self) -> str:
        return f'{self.catalog_id}:{self.component_id}'
    
    @property
    def product_ext_id(self) -> str:
        return self.component_ext_id
    
    @property
    def product_id(self) -> str:
        return self.component_id
    
    @property
    def export_dir(self) -> Path:
        return self.filepath.parent
    
    @property
    def meshes_dir(self) -> Path:
        return self.export_dir / 'meshes'
    
    @property
    def materials_dir(self) -> Path:
        return self.export_dir / 'materials'
    
    @property
    def components_dir(self) -> Path:
        d = self.export_dir / 'components'
        d.mkdir(exist_ok=True)
        return self.export_dir / 'components'
    
    @property
    def component_definition_file_name(self) -> str:
        name = self.component_ext_id.replace(':','_')
        ext = '.json'
        return f'{name}{ext}'
    



