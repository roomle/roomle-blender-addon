
from pathlib import Path
from subprocess import Popen
import zipfile
from io_mesh_roomle.enums import FILE_NAMES, MATERIALS_CSV_COLS
from io_mesh_roomle.material_exporter import MaterialCSVRow
from io_mesh_roomle.material_exporter._exporter import PBR_Channel
from io_mesh_roomle.roomle_script import get_valid_name
from test.utils import BLENDER, AddonExportParams, TestCaseExtended


def test_material_name_validation_RML_XXX():
    assert get_valid_name('some::name') == 'some_name'
    assert get_valid_name('some:_:name') == 'some___name'
    assert get_valid_name('some::::_::::name') == 'some___name'
    assert get_valid_name('some@name') == 'some_name'


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
            # cls.asset_path('combined-image-7dc4e4a0.glb'),
            Path('/Users/clemens/Library/CloudStorage/GoogleDrive-clemens.holleis@roomle.com/Meine Ablage/Assets/Smoketesting/Static Items/Stray_Truck.glb'),
            cls.fld / 'converted_glb.txt'
        )
        return super().setUpClass()

    def assert_txt(self,file, hash):
        assert (file).exists(), f'❌ file {file} does not exist'
        assert (file).is_file(), f'❌ {file} is not a file'
        assert self.sorted_txt_hash(self.fld / 'tags.csv') == hash, f'❌ {file} -> invalid hash'
        return True


    def test_file_tags_exist(self):
        assert self.assert_txt(self.fld / FILE_NAMES.TAGS_CSV, 'dbca80fd44c45596f39d425738c62071')

    def test_file_products_exist(self):
        self.assert_txt(self.fld / FILE_NAMES.ITEMS_CSV, 'dbca80fd44c45596f39d425738c62071')

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


    def test_texture_skipping_3b774e5c(self):
        m = MaterialCSVRow()
        p = PBR_Channel()
        
        m.set_texture(*p.map_data_as_tuple)
        assert m.dct == {}

        

    def test_materials_zip_content_NEW_3b774e5c(self):
        m = MaterialCSVRow()
        m.set_texture('img.jpg','THE_MAPPING')
        assert m.dct == {'tex0_image': 'img.jpg', 'tex0_mapping': 'THE_MAPPING', 'tex0_mmwidth': 1, 'tex0_mmheight': 1, 'tex0_tileable': True}
        m.set_texture(
            tex_image='a',
            tex_mapping='some mapping',
            tex_mmheight=10,
            tex_mmwidth=20,
            tex_tileable=False
            )
        assert m.dct == {
            'tex0_image': 'img.jpg', 'tex0_mapping': 'THE_MAPPING', 'tex0_mmwidth': 1, 'tex0_mmheight': 1, 'tex0_tileable': True,
            'tex1_image': 'a', 'tex1_mapping': 'some mapping', 'tex1_mmwidth': 20, 'tex1_mmheight': 10, 'tex1_tileable': False,
            }
        
    def test_materials_zip_content_PBR_Channel_3b774e5c(self):
        pc = PBR_Channel()
        pc.map = "some/path/to/image.png"  # type: ignore
        pc.mapping = "RGB"

        assert pc.map_data_as_tuple == ('zip://some/path/to/image.png', 'RGB', 1, 1, True)

        m = MaterialCSVRow()
        m.set_texture(*pc.map_data_as_tuple)

        assert m.dct == {'tex0_image': 'zip://some/path/to/image.png', 'tex0_mapping': 'RGB', 'tex0_mmwidth': 1, 'tex0_mmheight': 1, 'tex0_tileable': True}




    def test_materials_zip_content_NEW_2_3b774e5c(self):
        m = MaterialCSVRow()
        m.set('MY KEY', 'new value')
        assert m.dct == {'MY KEY' : 'new value'}

        m.set('MY KEY', 'overwrite')
        assert m.dct == {'MY KEY' : 'overwrite'}

        m.set('added key', 100)
        assert m.dct == {'MY KEY' : 'overwrite', 'added key': 100}


    def test_materials_zip_content_3b774e5c(self):

        zip_file = self.fld / FILE_NAMES.MATERIALS_ZIP
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(self.tmp_path)
        
        assert (self.tmp_path / 'materials.csv').exists()
        assert (self.tmp_path / 'Untitled.png').exists()
        assert self.sorted_txt_hash(self.tmp_path / 'materials.csv') == '7de0a818060a7ea36b347b7907aefaf8'

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

        assert self.sorted_txt_hash(self.tmp_path / 'catalog_id_converted_glb.json') == '400d1e7d3f0e858a7385a7d6e0a02330'
        assert self.sorted_txt_hash(self.tmp_path / 'components.csv') == '0afb4fa00585a7f54e1cee9e491ac0de'
        
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
