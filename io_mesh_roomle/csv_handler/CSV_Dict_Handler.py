import csv
from pathlib import Path
from typing import Union
from io_mesh_roomle.csv_handler.CSV_WriterBase import CSV_WriterBase



# class CSV_Dict_Handle r(CSV_WriterBase):
#     ...

class CSV_Dict_Handler(CSV_WriterBase):
    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._fieldnames: list[str] = []

    @property
    def fieldnames(self) -> tuple:
        return tuple(self._fieldnames)
    
    @property
    def rows(self) -> tuple:
        return tuple(self._rows)

    def _add_fields(self,*fields_to_add: str) -> None:
        for field in fields_to_add:
            if field not in self._fieldnames:
                self._fieldnames.append(field)  

    def add_row(self, data: dict):
        self._add_fields(*data.keys())
        for key,value in data.items():
            data[key] = self._evaluate_cell(value)

        self._rows.append(data)

    def add_rows(self, *data: dict):
        for line in data:
            self.add_row(line)
    
    def write(self, filepath: Path):
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames, quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            for row in self.rows:
                writer.writerow(row)