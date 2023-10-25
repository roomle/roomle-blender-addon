from pathlib import Path
from shutil import copy
from subprocess import Popen, call
import os
import unittest


from io_mesh_roomle import roomle_script
from test.utils import AddonExportParams, TestCaseExtended
from test.utils import BLENDER


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

class MaterialUnittests(TestCaseExtended):
    def test_material_csv_6c95a1b9(self):
        pass


