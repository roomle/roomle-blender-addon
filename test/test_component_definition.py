from dataclasses import dataclass
import inspect
import json
from pathlib import Path
from textwrap import dedent
from test import utils

from io_mesh_roomle.roomle_script import ComponentDefinition, MaterialParameterTag

@dataclass
class StaticStrings:
    catalog_id:str='some_id_ac583s'
    component_id:str='some_component_56a4'
    geometry_script_file = 'geometry_script-5dffc695.txt'
    placeholder = '::GEO-SCRIPT::'
    modiefied_geo = 'mod_geo_script-4b365528.txt'


class test_component_definition_creation(utils.TestCaseExtended):
    @classmethod
    def setUpClass(cls):
        cls.component_definition = ComponentDefinition(
            catalog_id=StaticStrings.catalog_id,
            component_id=StaticStrings.component_id,
            geometry_script=cls.asset_text(StaticStrings.geometry_script_file)
        )


    def test_static_fields(self):
        """check the static fields within the component defintion"""



        assert self.component_definition.external_id == f'{StaticStrings.catalog_id}:some_component_56a4'



        expected = self.dump_json(json.load(self.expectations_path('mat_params-39139e1a.json').open()), 'params-3656f286.json')
        actual = self.dump_json(self.component_definition.material_parameters_as_dict, 'mat_params_actual.json')
        
        assert self.component_definition.material_parameters_as_dict == self.expected_dict('mat_params-39139e1a.json')

        self.dump_txt(self.component_definition.component_definition, 'component_definition.txt')
        self.dump_txt(self.expectations_path('component_definition-76772eb6.txt').read_text(),'component_expected.txt')
        assert self.component_definition.component_definition == self.expect_text('component_definition-76772eb6.txt')

    def test_properties(self):
        """check computed properties"""
        assert self.component_definition.catalog_id == StaticStrings.catalog_id
        assert self.component_definition.component_id == StaticStrings.component_id
        assert self.component_definition.input_geometry_script == self.asset_text(StaticStrings.geometry_script_file)
        assert self.component_definition._place_holder == StaticStrings.placeholder
        assert self.component_definition.mod_geo_script == self.expect_text(StaticStrings.modiefied_geo)
    
    def test_type_of_material_definitions(self):
        mat_params = self.component_definition.material_parameters
        for ma in mat_params:
            assert isinstance(ma, MaterialParameterTag)

