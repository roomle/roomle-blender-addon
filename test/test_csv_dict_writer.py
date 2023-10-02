from pathlib import Path
from io_mesh_roomle.csv_handler.CSV_Dict_Handler import CSV_Dict_Handler
from test.utils import TestCaseExtended


class TestCsvDict(TestCaseExtended):

    def test_header_6c04739e(self):

        output = self.tmp_path / 'out.csv'

        handler = CSV_Dict_Handler()
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

        assert self.sorted_txt_hash(
            output) == '1aedfc93cb3b303c236b5da3e3b05bc6'

    def test_iterable_field(self):
        output = self.tmp_path / 'out-3.csv'

        handler = CSV_Dict_Handler()
        handler.add_rows(
            {'iterable': ['test', 'some', 'strings']},
            {'field two': 1234},
            {'field two': 'with "quotes" in string'},
            {'iterable': ('test', 67.34, 324)},
            {'path': Path('/var/some-folder')}
        )
        handler.write(output)

        assert self.sorted_txt_hash(
            output) == '9b3058e9d0b07d46e906c2ce4bb0f6bb'
