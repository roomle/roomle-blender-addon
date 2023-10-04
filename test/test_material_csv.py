
from pathlib import Path
from subprocess import Popen
import zipfile
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
        assert self.assert_txt(self.fld / "tags.csv", 'bdce74035c6fe28383965318adad8672')

    def test_file_products_exist(self):
        self.assert_txt(self.fld / 'products.csv', 'bdce74035c6fe28383965318adad8672')

    def test_file_meta_exist(self):
        assert (self.fld / "meta.json").exists()
        assert (self.fld / "meta.json").is_file()
        assert self.sorted_txt_hash(self.fld / 'meta.json') == '2aac45258652ad664a672bba413834de'

    def test_file_meshes_exist(self):
        assert (self.fld / "meshes.zip").exists()
        assert (self.fld / "meshes.zip").is_file()

    def test_file_materials_exist(self):
        assert (self.fld / "materials.zip").exists()
        assert (self.fld / "materials.zip").is_file()

    def test_file_components_exist(self):
        assert (self.fld / "components.zip").exists()
        assert (self.fld / "components.zip").is_file()


    def test_materials_zip_content(self):
        zip_file = self.fld / "materials.zip"
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(self.tmp_path)
        
        assert (self.tmp_path / 'materials.csv').exists()
        assert (self.tmp_path / 'Untitled.png').exists()
        assert self.sorted_txt_hash(self.tmp_path / 'materials.csv') == '5f0af20172288dae2460e91e33546153'

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

        assert self.sorted_txt_hash(self.tmp_path / 'catalog_id_converted_glb.json') == 'e505c15d74c7646d6d816bebddd8c38e'
        assert self.sorted_txt_hash(self.tmp_path / 'components.csv') == 'ccb75cc56e0a171dfc7c1783a95a24c0'
        
class TestRoomleExportAlt(TestCaseExtended):
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
