

from pathlib import Path
from typing import Callable
from io_mesh_roomle import arguments
from test.utils import TestCaseExtended


class TestAddonArguments(TestCaseExtended):
    expected_static_fields = {
        'filepath': Path(),
        'catalog_id': str(),
        'use_selection': bool(),
        'export_normals': bool(),
        'export_materials': bool(),
        'apply_rotations': bool(),
        'use_corto': bool(),
        'mesh_export_option': str(),
        'uv_float_precision': int(),
        'normal_float_precision': int(),
        'component_id': str(),
        'debug': bool(),
    }

    expected_function_parameters = (
        'from_dict',
        'to_dict',
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.instance = arguments._AddonArguments.from_dict(cls.expected_static_fields)
        cls.class_name_to_test = arguments._AddonArguments.__name__
        return super().setUpClass()
    

    def test_addon_args_static(self):
        ex_args = self.expected_static_fields
        args = self.instance

        expected = list(ex_args.keys())

        for field in dir(args):
            if field.startswith('_'):
                continue
            af = getattr(args, field)
            if isinstance(af, Callable):
                continue
            assert field in ex_args, f'field `{field}` was not expected in `{self.class_name_to_test}`'
            del expected[expected.index(field)]

        assert len(expected) == 0, f'expected fields in `{self.class_name_to_test}` are missing `{expected}`'

    def test_addon_args_dict(self):
        ex_args = self.expected_function_parameters
        args = self.instance

        expected = list(ex_args)

        for field in dir(args):
            if field.startswith('_'):
                continue
            af = getattr(args, field)
            if isinstance(af, Callable):
                assert field in ex_args, f'method `{field}` was not expected in `{self.class_name_to_test}`'
                del expected[expected.index(field)]

        assert len(expected) == 0, f'expected methods in `{self.class_name_to_test}` are missing `{expected}`'

class TestArgumentsProperties(TestCaseExtended):
    expected_properties = {
        'component_tag': str(),
        'component_tag_label_en': str(),
        'catalog_root_tag': str(),
        'component_ext_id': str(),
        'product_ext_id': str(),
        'product_id': str(),
        'export_dir': Path(),
        'meshes_dir': Path(),
        'materials_dir': Path(),
        'components_dir': Path(),
        'component_definition_file_name': str(),
        'component_label': str(),
        'product_label': str(),
    }


    @classmethod
    def setUpClass(cls) -> None:
        cls.instance = arguments.ArgsStore.from_dict(TestAddonArguments.expected_static_fields)
        cls.skip_static_args = tuple(TestAddonArguments.expected_static_fields.keys())
        cls.class_name_to_test = arguments.ArgsStore.__name__
        return super().setUpClass()
    

    def test_addon_args_static(self):
        ex_args = self.expected_properties
        args = self.instance

        expected = list(ex_args.keys())

        for field in dir(args):
            if field.startswith('_'):
                continue
            af = getattr(args, field)
            if isinstance(af, Callable):
                continue
            if field in self.skip_static_args:
                continue
            assert field in ex_args, f'property `{field}` was not expected in `{self.class_name_to_test}`'
            del expected[expected.index(field)]

        assert len(expected) == 0, f'expected fields in `{self.class_name_to_test}` are missing `{expected}`'
