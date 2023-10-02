from hashlib import md5
import json
from pathlib import Path
from typing import Union


import logging
import unittest


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
    def expected_dict(cls, filename: str) -> dict:
        return cls._read_file_json_to_dict(cls.expectations / filename)

    @classmethod
    def asset_text(cls, filename: str) -> str:
        return cls._read_file_text(cls.assets / filename)

    @classmethod
    def asset_dict(cls, filename: str) -> dict:
        return cls._read_file_json_to_dict(cls.assets / filename)


    @property
    def tmp_path(self):
        tmp_path = Path(__file__).parent.parent.parent.absolute() / 'tmp' / self.__class__.__name__
        tmp_path.mkdir(exist_ok=True, parents=True)
        return tmp_path

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


class TestCaseExtended(unittest.TestCase, AssetHandling, Assertions):

    __logger: logging.Logger