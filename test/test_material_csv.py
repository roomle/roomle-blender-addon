
from pathlib import Path
from subprocess import Popen
import zipfile
from io_mesh_roomle.enums import FILE_NAMES
from test.utils import BLENDER, AddonExportParams, TestCaseExtended


class TestMaterialCSV(TestCaseExtended):
    def test_mat_csv(self):


        params = AddonExportParams(
            filepath=str(self.tmp_path / 'out.txt')
        )

        file = self.asset_path('combined-image-7dc4e4a0.glb')

        Popen([
            BLENDER,
            '--background',
            '--python', Path(__file__).parent / 'simple_export.py',
            '--', file, params.json
        ]).wait()
        pass

class TestRoomleExport(TestCaseExtended):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fld = cls.tmp_path_class() / 'shared'
        cls.fld.mkdir(exist_ok=True)
        cls.convert_file(
            cls.asset_path('combined-image-7dc4e4a0.glb'),
            cls.fld / 'converted_glb.txt'
        )
        return super().setUpClass()

    def assert_txt(self,file, hash):
        assert (file).exists(), f'❌ file {file} does not exist'
        assert (file).is_file(), f'❌ {file} is not a file'
        assert self.sorted_txt_hash(self.fld / 'tags.csv') == hash, f'❌ {file} -> invalid hash'
        return True


    def test_file_tags_exist(self):
        assert self.assert_txt(self.fld / FILE_NAMES.TAGS_CSV, 'c225058a07e822c067b7f7a56b90d368')

    def test_file_products_exist(self):
        self.assert_txt(self.fld / FILE_NAMES.ITEMS_CSV, 'c225058a07e822c067b7f7a56b90d368')

    def test_file_meta_exist(self):
        assert (self.fld / FILE_NAMES.META_JSON).exists()
        assert (self.fld / FILE_NAMES.META_JSON).is_file()
        assert self.sorted_txt_hash(self.fld / FILE_NAMES.META_JSON) == 'efccba29e24e518c81a111d62a04fe48'

    def test_file_meshes_exist(self):
        assert (self.fld / FILE_NAMES.MESHES_ZIP).exists()
        assert (self.fld / FILE_NAMES.MESHES_ZIP).is_file()

    def test_file_materials_exist(self):
        assert (self.fld / FILE_NAMES.MATERIALS_ZIP).exists()
        assert (self.fld / FILE_NAMES.MATERIALS_ZIP).is_file()

    def test_file_components_exist(self):
        assert (self.fld / FILE_NAMES.COMPONENTS_ZIP).exists()
        assert (self.fld / FILE_NAMES.COMPONENTS_ZIP).is_file()


    def test_materials_zip_content(self):
        zip_file = self.fld / FILE_NAMES.MATERIALS_ZIP
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(self.tmp_path)
        
        assert (self.tmp_path / 'materials.csv').exists()
        assert (self.tmp_path / 'Untitled.png').exists()
        assert self.sorted_txt_hash(self.tmp_path / 'materials.csv') == '11bea795a679183acc38e2c817effe7c'

    def test_meshes_zip_content(self):
        zip_file = self.fld / "meshes.zip"
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(self.tmp_path)
        
        assert len(tuple(self.tmp_path.glob('*.obj'))) == 5

    def test_components_zip_content(self):
        zip_file = self.fld / "components.zip"
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(self.tmp_path)
        
        assert (self.tmp_path / 'catalog_id_converted_glb.json').exists()
        assert (self.tmp_path / 'catalog_id_converted_glb.json').is_file()
        assert (self.tmp_path / 'components.csv').exists()
        assert (self.tmp_path / 'components.csv').is_file()

        assert self.sorted_txt_hash(self.tmp_path / 'catalog_id_converted_glb.json') == '03ce2fb5202e232713be15b1b9dc9451'
        assert self.sorted_txt_hash(self.tmp_path / 'components.csv') == '4f622ee19d187a3655ae0126609e532c'
        
class RoomleExportAlt(TestCaseExtended):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fld = cls.tmp_path_class() / 'shared'
        cls.fld.mkdir(exist_ok=True)


        params = AddonExportParams(
            filepath=str(cls.fld / 'converted_glb.txt'),
            export_materials=False,
        )

        file = cls.asset_path('combined-image-7dc4e4a0.glb')

        Popen([
            BLENDER,
            '--background',
            '--python', Path(__file__).parent / 'simple_export.py',
            '--', file, params.json
        ]).wait()
        pass
        return super().setUpClass()

    def test_no_material_export(self):
        pass
