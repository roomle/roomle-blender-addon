import csv
from pathlib import Path
from typing import Union


class CSV_WriterBase:
    def __init__(self,*rows: Union[list,tuple]) -> None:
        self.rows: list = list(self._evaluate_row(row) for row in rows)


    @staticmethod
    def _evaluate_row(row: Union[tuple,list]) -> tuple:
        new_row = []
        for cell in row:
            new_row.append(
                CSV_WriterBase._evaluate_cell(cell)
                )
        return tuple(new_row)
    
    @staticmethod
    def _evaluate_cell(cell: Union[str,int,float,tuple,list]) -> Union[str, float, int]:
        if isinstance(cell,(list, tuple)):
            str_col = [str(i) for i in cell]
            return ' '.join(str_col)
        elif isinstance(cell, (int,float,str)):
            return cell
        elif cell == None:
            return cell
        else:
            return str(cell)


    def write(self, filepath: Union[str,Path]) -> Path:
        filepath = Path(filepath)
        with open(filepath, 'w', newline='') as file:
            writer = csv.writer(file, quoting=csv.QUOTE_NONNUMERIC)
            for row in self.rows:
                writer.writerow(row)
        return filepath
    

