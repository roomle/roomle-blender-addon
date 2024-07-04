import csv
import json
from pathlib import Path
from typing import Union


class _CSV_WriterBase:

    @staticmethod
    def _evaluate_cell(cell: Union[str, int, float, tuple, list]) -> Union[str, float, int]:
        """handle different data types in a given cell

        Args:
            cell (Union[str, int, float, tuple, list]):cell data

        Returns:
            Union[str, float, int]: possible supported output data
        """
        if isinstance(cell, (list, tuple)):
            str_col = [str(i) for i in cell]
            return ' '.join(str_col)
        elif isinstance(cell, (int, float, str)):
            return cell
        elif cell == None:
            return cell
        else:
            return str(cell)
        
    def write(self):
        """will be handled by the subclass"""
        ...

class _CSV_DictHandler(_CSV_WriterBase):
    """create csv files from dictionaries"""

    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._fieldnames: list[str] = []

    @property
    def fieldnames(self) -> tuple:
        return tuple(self._fieldnames)

    @property
    def rows(self) -> tuple[dict, ...]:
        return tuple(self._rows)

    def add_fields(self, *fields_to_add: str) -> None:
        """add fields. can be uesed to add empty colums.
        also use it to create a certeain order of columns
        """
        for field in fields_to_add:
            if field not in self._fieldnames:
                self._fieldnames.append(field)

    def add_row(self, data: dict) -> None:
        """add a single row by providing one dict.
        fields will be automatically added if needed

        Args:
            data (dict): key value combination of data to add
        """
        self.add_fields(*data.keys())
        for key, value in data.items():
            data[key] = self._evaluate_cell(value)

        self._rows.append(data)

    def add_rows(self, *data: dict) -> None:
        """add mutiple rows by providing multiple dicts as parameters"""
        for line in data:
            self.add_row(line)

    @property
    def rows_sorted(self):
        """return the row data sorted by the first column"""
        if len(self.fieldnames) == 0:
            return []
        first_column = self.fieldnames[0]
        row_keys_to_sort: list[str] = []
        lookup_table: dict[str, dict] = {}
        for row in self.rows:
            if first_column in row:
                segment_a = row[first_column]
            else:
                segment_a = "Z"
            segment_b = json.dumps(row)
            row_key = f'{segment_a}-{segment_b}'
            row_keys_to_sort.append(row_key)
            lookup_table[row_key] = row
        row_keys_to_sort.sort()
        return[lookup_table[i] for i in row_keys_to_sort]

    def write(self, filepath: Path):
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=self.fieldnames, quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            for row in self.rows_sorted:
                writer.writerow(row)


class CSV_Writer(_CSV_DictHandler):
    """Write CSV files from dictionaries"""
    ...
