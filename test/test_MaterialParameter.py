from dataclasses import dataclass
import inspect
import json
from pathlib import Path
from textwrap import dedent
from unittest import TestCase

from attr import field
from test import utils

from io_mesh_roomle.roomle_script import ComponentDefinition, MaterialParameterTag


class test_material_parameter(utils.TestCaseExtended):
    @classmethod
    def setUpClass(cls):
        cls.mp = MaterialParameterTag('catalog_id','component_id','material_id')

    def tearDown(self) -> None:
        MaterialParameterTag._counter=0

    
    def test_properties_and_fields(self):

        # get a
        found_fields = set((field for field in dir(self.mp) if not field.startswith('__') and not field.endswith('__')))

        expected_fields = set([
                        '_counter',
                        '_get_number',
                        'as_dict',
                        'key',
                        'label_en',
                        'material_ext_id',
                        'num',
                        'tag_id',
                        'csv_row',
                        'catalog_id',
                        'component_id',
                        'material_id',
                        ])
        
        assert found_fields - expected_fields == set()
        assert expected_fields - found_fields == set()
        
        pass


    def test_static_fields_d0e476bf(self):
        assert self.mp.num == 1
        assert self.mp.material_ext_id == 'catalog_id:component_id_material_id'
        assert self.mp.key == 'material_001'
        assert self.mp.label_en == 'material id (component_id)'
        assert self.mp.tag_id == 'component_id_material_id'
        self.dump_json(self.mp.as_dict, '11c11e81-51ee-4fbd-bc38-f4781b825c2b')
        assert self.mp.as_dict == self.expected_dict(
            'material_parameters_as_dict-cb382cf9.json')
    
    def test_counter(self):
        a = MaterialParameterTag("_","_","_")
        b = MaterialParameterTag("_","_","_")
        c = MaterialParameterTag("_","_","_")
        assert a.num == 2
        assert b.num == 3
        assert c.num == 4


