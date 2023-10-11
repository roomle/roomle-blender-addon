
import json
from test.utils import JsonUtils, TestCaseExtended
from test import utils


# class TestJsonUtils(TestCaseExtended):

#     def test_load(self):
#         JsonUtils._load('test')

class JsonOrdered(TestCaseExtended):
    @classmethod
    def setUpClass(cls) -> None:
        cls.obj_a = {
            "13": {
                "nested_key_a" : "d4278a43",
                "nested_key_b" : "d4278a43",
                "inner list": [
                    0,1,2,3,4,5,6,7,8,9
                ]
            },
            "another_field": "a string component",
            "field_a": "a string component",
        }
        cls.obj_b = {
            "field_a": "a string component",
            "13": {
                "nested_key_b" : "d4278a43",
                "inner list": [
                    6,7,8,2,9,0,1,3,4,5
                ],
                "nested_key_a" : "d4278a43",
            },
            "another_field": "a string component",
        }
        cls.obj_c = {
            "13": {
                "field_a": "a string component",
                "nested_key_b" : "d4278a43",
                "inner list": [
                    6,7,8,2,9,0,1,3,4,5
                ],
                "nested_key_a" : "d4278a43",
            },
            "another_field": "a string component",
        }
        return super().setUpClass()
    
    def test_basic_usage(self):
        assert self.obj_a != self.obj_b
        assert utils.JsonUtils.ordered_json(self.obj_b) == utils.JsonUtils.ordered_json(self.obj_a)
        assert utils.JsonUtils.ordered_json(self.obj_b) != utils.JsonUtils.ordered_json(self.obj_c)
        pass

class JsonDumpSorted(TestCaseExtended):
    def test_dump_sorted(self):
        data = {
            "b":(3,1,2),
            "a":1,
            "c":3,
        }
        file = self.tmp_path / 'sorted_ouput.json'
        JsonUtils.dump_file_sorted(data, file)
        data_new = file.read_text()
        assert data_new == '[["a", 1], ["b", [1, 2, 3]], ["c", 3]]'