from typing import Union
from io_mesh_roomle.csv_handler.CSV_WriterBase import CSV_WriterBase


class CSV_Line_Handler(CSV_WriterBase):

    def add_line(self, *fields):
        self.rows.append(self._evaluate_row(fields))
        return self

    def add_lines(self, *lines: Union[tuple, list]):
        for line in lines:
            self.add_line(*line)
        return self