
from hashlib import md5
import inspect
import logging
from pathlib import Path
import re
import sys
import textwrap
from typing import Any


sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
import io_mesh_roomle
# from io_mesh_roomle.roomle_script import MaterialTag


class Writer:

    def __init__(self,file_path:Path):

        self.output_file = file_path
        self.name = md5(str(file_path).encode('utf-8')).hexdigest()
        self.__logger_instance = self._get_logger(self.output_file, self.name)
        self.__output_fn = self.__logger_instance.info

    @staticmethod
    def _get_logger(file_path: Path, name: str):
        log = logging.getLogger(name)
        log.level = logging.DEBUG
        log.propagate=False
        fh = logging.FileHandler(
            filename=file_path
        )
        log.addHandler(fh)
        return log

    def write(self, message:str):
        return self.__output_fn(textwrap.dedent(message))
    
    def __call__(self, message:str) -> Any:
        return self.write(message)


def test_file_saves(tmp_path: Path):
    """find save file calls that may be left over during dev

    Args:
        tmp_path (Path): _description_
    """
    wrt = Writer(tmp_path / 'found.log')

    patterns = (
        r'(?<!# )bpy\.ops\.wm\.save_as_mainfile\(',
    )

    counter = 0
    root = Path(inspect.getfile(io_mesh_roomle)).parent
    for py_file in root.rglob('*.py'):
        content = py_file.read_text()
        for line_number,content in enumerate(content.split('\n')):
            line_number += 1
            for pattern in patterns:
                finds = re.findall(pattern,content)
                if bool(finds):
                    ln = '='*80
                    wrt((f"""\
                        {ln}
                        `{finds[0]}` found in
                        {py_file}: {line_number}
                        """))
                    counter += 1

    assert counter == 0, f'check: {wrt.output_file}'








   