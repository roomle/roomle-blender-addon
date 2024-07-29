from pathlib import Path
from textwrap import dedent
from io_mesh_roomle.csv_handler import _CSV_DictHandler
from test.utils import AssetHandling, TestCaseExtended


class TestCsvDict(TestCaseExtended):

    def test_header_6c04739e(self):

        output = self.tmp_path / 'out.csv'

        handler = _CSV_DictHandler()
        handler.add_row({'field a': 'a9af025c'})
        handler.add_row({'field b': 'd5d2d3e9'})
        handler.add_row({
            'field c': '91064ccb',
            'field b': '9df6754f',
            'field e': None,
        })

        assert isinstance(handler.rows, tuple)
        assert isinstance(handler.fieldnames, tuple)
        assert isinstance(handler.fieldnames, tuple)
        handler.write(output)

        assert output.read_text() == AssetHandling.expect_text("out-e32ad02f.csv")


    def test_iterable_field(self):
        output = self.tmp_path / 'out-3.csv'

        handler = _CSV_DictHandler()
        handler.add_rows(
            {'iterable': ['test', 'some', 'strings']},
            {'field two': 1234},
            {'field two': 'with "quotes" in string'},
            {'iterable': ('test', 67.34, 324)},
            {'path': Path('/var/some-folder')}
        )
        handler.write(output)

        assert output.read_text() == AssetHandling.expect_text("out-1ffd2c51.csv")

    
    def test_blank_field_creation(self):
        out = self.tmp_path / 'out-fields.csv'
        handler = _CSV_DictHandler()
        handler.add_fields('one','two')
        handler.add_fields('three')
        handler.write(out)
        assert out.read_text() == '"one","two","three"\n'

    def test_sorted_output(self):

        
        handler = _CSV_DictHandler()
        handler.add_row({"a":'z'})
        handler.add_row({"b":'z', "a":"c"})
        handler.add_row({"d":'a', "a":"a"})
        handler.write(self.tmp_path / 'out-sorted.csv')

        assert (self.tmp_path / 'out-sorted.csv').read_text() == dedent("""\
                                                                        "a","b","d"
                                                                        "a","","a"
                                                                        "c","z",""
                                                                        "z","",""
                                                                        """)
        
