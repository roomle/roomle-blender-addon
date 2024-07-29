from dataclasses import dataclass
from hashlib import md5
import inspect
import json
from pathlib import Path
import shutil
from subprocess import Popen
from typing import Any, Union


import logging
import unittest


class JsonUtils:

    @staticmethod
    def ordered_json(obj):
        if isinstance(obj, dict):
            return sorted((k, JsonUtils.ordered_json(v)) for k, v in obj.items())
        if isinstance(obj, (list, tuple)):
            return sorted(JsonUtils.ordered_json(x) for x in obj)
        else:
            return obj

    
    @staticmethod
    def dump_file_sorted(data, filepath: Path) -> Path:
        sorted_data = JsonUtils.ordered_json(data)
        filepath.write_text(json.dumps(sorted_data))
        return filepath
    
    @staticmethod
    def _load(resource: Union[str, Path, dict, list, tuple]) -> Any:
        if isinstance(resource, str):
            data = json.loads(resource)
            # json.decoder.JSONDecodeError
            # try:
            # except Exception as e:
            #     pass


class AssetHandling:
    expectations: Path
    assets:Path

    assets = Path(__file__).parent.parent / 'assets'
    expectations = assets / 'expectations'

    @staticmethod
    def _read_file_text(file:Path) -> str:
        return file.read_text()

    @staticmethod
    def _read_file_json_to_dict(file:Path) -> dict:
        return json.loads(TestCaseExtended._read_file_text(file))

    @classmethod
    def expect_text(cls, filename: str) -> str:
        return cls._read_file_text(cls.expectations / filename)
    
    @classmethod
    def expect_json(cls, filename: str) -> dict:
        return json.loads(cls._read_file_text(cls.expectations / filename))


    def expected_dict(self, filename: str) -> dict:

        data = self._read_file_json_to_dict(self.expectations / filename)
        self.dump_json(data, 'expected.json')
        return data

    @classmethod
    def asset_text(cls, filename: str) -> str:
        return cls._read_file_text(cls.assets / filename)

    @classmethod
    def asset_dict(cls, filename: str) -> dict:
        return cls._read_file_json_to_dict(cls.assets / filename)
    
    @classmethod
    def asset_path(cls, filename: str) -> Path:
        return cls.assets / filename
    
    def expectations_path(cls, filename: str) -> Path:
        return cls.expectations / filename

    def compare_json_vs_expected_file(self, name: str, data, filename):

        ex_file = self.expectations_path(filename)
        shutil.copy(ex_file, self.tmp_path / f'{name}-expected.json')

        
        json.dump(data, (self.tmp_path / f'{name}-actual.json').open())


    @classmethod
    def tmp_path_class(cls):
        tmp_path = Path(__file__).parent.parent.parent.absolute() / 'tmp' / cls.__name__
        tmp_path.mkdir(exist_ok=True, parents=True)
        return tmp_path
    
    @property
    def tmp_path(self) -> Path:
        """searches the test method name inside the callstack
        and generates a folder with the same name

        Returns:
            _type_: _description_
        """
        # find the internal function that called the test method -> our method is index -1 from this
        method_caller_name = '_callTestMethod'

        # put all names of the call stack into one tuple
        call_stack_names = tuple((frame[3] for frame in inspect.stack()))

        if method_caller_name in call_stack_names:
            index_of_caller_in_stack = call_stack_names.index(method_caller_name)
            frame_name = call_stack_names[index_of_caller_in_stack-1]
        else:
            # in case if we could not find the method, generate a unique folder name
            frame_name = 'unknown-' + md5((','.join(list(call_stack_names))).encode('utf-8')).hexdigest()[:8]

        new_folder = self.tmp_path_class() / frame_name
        new_folder.mkdir(exist_ok=True, parents=True)
        return new_folder


    def dump_txt(self, data: str, filename: str) -> Path:
        file = self.tmp_path / filename
        file.write_text(data)
        return file

    def dump_json(self, data: Union[dict, list, tuple], filename: str) -> Path:
        return self.dump_txt(json.dumps(data, indent=4), filename)


class Assertions:

    def sorted_txt_hash(self, filepath: Path):
        """create a md5 of a csv file after sorting the rows
        this is useful if the order of the rows can alter by
        using a generator or async functions

        Args:
            csv_file (Path): path to the csv file

        Returns:
            str: md5 of the sorted content
        """

        file_content = filepath.read_text().split('\n')
        file_content.sort()
        file_content = '\n'.join(file_content).encode('utf8')

        return md5(file_content).hexdigest()


BLENDER = '/Applications/Blender3.6.2-ARM-LTS.app/Contents/MacOS/blender'


@dataclass
class AddonExportParams:
    filepath: str
    catalog_id: str='catalog_id'
    mesh_export_option: str="EXTERNAL"
    use_corto: bool = False
    export_materials: bool = True

    @property
    def json(self):
        return json.dumps(self.__dict__)


class BlenderRunner(AssetHandling):

    @staticmethod
    def convert_file(file:Path, output: Path):

        params = AddonExportParams(
            filepath=str(output)
        )


        cmd = [
            BLENDER,
            '--background',
            '--python', Path(__file__).parent.parent / 'simple_export.py',
            '--', file, params.json
        ]
        out_file = Path(__file__).parent.parent.parent / 'tmp/blender_log.log'
        with out_file.open('w') as out:
            Popen(cmd,stdout=out).wait()


class TestCaseExtended(unittest.TestCase, Assertions, BlenderRunner):

    __logger: logging.Logger