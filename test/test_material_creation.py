from pathlib import Path
from shutil import copy
from subprocess import Popen, call
import os
import json
import unittest

from attr import dataclass

from io_mesh_roomle import roomle_script

BLENDER = '/Applications/Blender3.6.2-ARM-LTS.app/Contents/MacOS/blender'


@dataclass
class Params:
    filepath: str
    catalog_id: str='catalog_id'
    mesh_export_option: str="EXTERNAL"
    use_corto: bool = False
    export_materials: bool = True

    @property
    def json(self):
        return json.dumps(self.__dict__)


def test_materials(tmp_path):

    params = Params(
        filepath=str(tmp_path / 'out.txt')
    )

    file = Path('/Users/clemens/Dev/git/DAP-AssetFactory/test/data/static_item_conversion/combined-image.glb')

    Popen([
        BLENDER,
        '--background',
        '--python', Path(__file__).parent / 'simple_export.py',
        '--', file, params.json
    ]).wait()
    pass


def test_args(tmp_path: Path):
    s = tmp_path / 'script.py'
    s.write_text(
        "\nimport bpy"
        "\nfrom pathlib import Path"
        "\n(Path(__file__).parent / 'read.txt').write_text(repr(bpy.ops.export_mesh.roomle_script))"
    )
    

    Popen([
        BLENDER,
        '--background',
        '--python', s
    ]).wait()

    result = tmp_path / 'read.txt'
    assert result.is_file()
    txt = result.read_text()

    assert txt.startswith('bpy.ops.export_mesh.roomle_script(')

    # TODO: add check for params

class MaterialUnittests(unittest.TestCase):
    def test_first(self):
        pass

