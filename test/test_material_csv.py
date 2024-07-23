
import json
from pathlib import Path
from subprocess import Popen
import zipfile
from io_mesh_roomle.enums import FILE_NAMES 
from io_mesh_roomle.material_exporter import MaterialCSVRow
from io_mesh_roomle.material_exporter._exporter import PBR_Channel
from io_mesh_roomle.roomle_script import get_valid_name
from test.utils import BLENDER, AddonExportParams, AssetHandling, TestCaseExtended


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
        assert AssetHandling.expect_text("tags-12302b60.csv") == (self.fld / FILE_NAMES.TAGS_CSV).read_text()


    def test_file_products_exist(self):
        assert AssetHandling.expect_text("items-92106a8e.csv") == (self.fld / FILE_NAMES.ITEMS_CSV).read_text()

    def test_file_meta_exist(self):
        assert (self.fld / FILE_NAMES.META_JSON).exists()
        assert (self.fld / FILE_NAMES.META_JSON).is_file()
        assert AssetHandling.expect_text("meta-eab00086.json") == (self.fld / FILE_NAMES.META_JSON).read_text()

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
        
        m.add_texture_field(*p.texture_map_data_as_tuple)
        assert m.data_dict == {}

        

    def test_materials_zip_content_NEW_3b774e5c(self):
        m = MaterialCSVRow()
        m.add_texture_field('img.jpg','THE_MAPPING')
        assert m.data_dict == {'tex0_image': 'img.jpg', 'tex0_mapping': 'THE_MAPPING', 'tex0_mmwidth': 1, 'tex0_mmheight': 1, 'tex0_tileable': True}
        m.add_texture_field(
            tex_image='a',
            tex_mapping='some mapping',
            tex_mmheight=10,
            tex_mmwidth=20,
            tex_tileable=False
            )
        assert m.data_dict == {
            'tex0_image': 'img.jpg', 'tex0_mapping': 'THE_MAPPING', 'tex0_mmwidth': 1, 'tex0_mmheight': 1, 'tex0_tileable': True,
            'tex1_image': 'a', 'tex1_mapping': 'some mapping', 'tex1_mmwidth': 20, 'tex1_mmheight': 10, 'tex1_tileable': False,
            }
        
    def test_materials_zip_content_PBR_Channel_3b774e5c(self):
        pc = PBR_Channel()
        pc.map = "some/path/to/image.png"  # type: ignore
        pc.mapping = "RGB"

        assert pc.texture_map_data_as_tuple == ('zip://some/path/to/image.png', 'RGB', 1, 1, True)

        m = MaterialCSVRow()
        m.add_texture_field(*pc.texture_map_data_as_tuple)

        assert m.data_dict == {'tex0_image': 'zip://some/path/to/image.png', 'tex0_mapping': 'RGB', 'tex0_mmwidth': 1, 'tex0_mmheight': 1, 'tex0_tileable': True}




    def test_materials_zip_content_NEW_2_3b774e5c(self):
        m = MaterialCSVRow()
        m.set_field('MY KEY', 'new value')
        assert m.data_dict == {'MY KEY' : 'new value'}

        m.set_field('MY KEY', 'overwrite')
        assert m.data_dict == {'MY KEY' : 'overwrite'}

        m.set_field('added key', 100)
        assert m.data_dict == {'MY KEY' : 'overwrite', 'added key': 100}


    def test_materials_zip_content_3b774e5c(self):

        zip_file = self.fld / FILE_NAMES.MATERIALS_ZIP
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(self.tmp_path)
        
        assert (self.tmp_path / 'materials.csv').exists()
        assert (self.tmp_path / 'Untitled.png').exists()
        assert AssetHandling.expect_text('materials-23e1669f.csv') == (self.tmp_path / 'materials.csv').read_text()

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

        assert json.load((self.tmp_path / 'catalog_id_converted_glb.json').open('r')) == AssetHandling.expect_json('catalog_id_converted_glb-413e5b37.json')
        assert (self.tmp_path / 'components.csv').read_text() == AssetHandling.expect_text('components-d73f238c.csv')
        
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
# TODO: Add test that loads a gltf, exports it to material v2 and compares to a saved expected version