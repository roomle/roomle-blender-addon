from io_mesh_roomle.csv_handler import CSV_Writer

from hashlib import md5
from pathlib import Path

from io_mesh_roomle.csv_handler.CSV_Line_Handler import CSV_Line_Handler
from test.utils import TestCaseExtended


class Test_CSV_Writer(TestCaseExtended):

    def test_do_0f93cfd5(self):
        file = self.tmp_path / 'out-1.csv'
        CSV_Line_Handler(
            (1,2,3,6),
            (1,["item a", "item b", 90],3.897),
            (1,"some, string here",3),
            ('"with quotes " inside"',),
            (Path('/some/path').absolute(),),
            (102, 369.58, (986, 963.2, "comma, test")),
        ).write(file)
        assert md5(file.read_bytes()).hexdigest() == '6d79da2a665ff91e6919183b1dddb11d'

    def test_add_line_0f93cfd5(self):
        file = self.tmp_path / 'out-2.csv'
        (CSV_Line_Handler()
        .add_line(1,2,4,3,4)
        .add_line('tuple','in field, one')
        .add_line(*['de','construct'],'list')
        .write(file))
        pass
        assert md5(file.read_bytes()).hexdigest() == '060e27e4912ca0d5666b933f2212d966'

    def test_add_lines_0f93cfd5(self):
        file = self.tmp_path / 'out.csv'

        (CSV_Line_Handler()
        .add_lines((1,),(2,),("three",))
        .add_lines((4,'line', 5 , "here"),["END"])
        .write((file)))
        pass
        assert md5(file.read_bytes()).hexdigest() == 'f0033ad94d3ee1d23f9f6d426cb976f9'