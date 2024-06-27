from enum import Enum, unique
from pathlib import Path
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union
import json
import csv

import logging

log = logging.getLogger('material-csv')

@dataclass
class DataClassJSONMixin():
    def to_json(self):
        pass
        dict = self.__dict__
        for key, value in dict.items():
            if "to_json" not in dir(value):
                continue
            dict[key] = json.loads(value.to_json())

        return json.dumps(self.__dict__)

class CsvLine(ABC):
    def print_line(self):
        pass



class RoomleTextureImage:
    def __init__(self) -> None:
        self.tileable: bool = True
        self.image: str = ''
        self.mapping: str = ''
        self.width_mm: int = 1
        self.height_mm: int = 1

    def dump_list(self) -> List:
        return [
            self.tileable,
            self.image,
            self.mapping,
            self.width_mm,
            self.height_mm
        ]


@dataclass
class BaseColor(DataClassJSONMixin):
    r: float = 1
    g: float = 1
    b: float = 1

    def set(self, *args):
        try:
            (
                self.r,
                self.g,
                self.b
            ) = [round(x,2) for x in args]
        except Exception as e:
            log.warning(e)

@unique
class TextureMapping(str,Enum):
    #* V1 Mappings
    RGB='RGB'
    RGBA='RGBA'
    XYZ='XYZ'
    ORM='ORM'

    #* V2 Mappings
    # https://roomle.atlassian.net/wiki/spaces/DT/pages/2255650817/Material+Definition+V2
        
    EMRGB='EMRGB'
    CCRG='CCRG'
    CCXYZ='CCXYZ'
    SHRGBA='SHRGBA'
    SPRGBA='SPRGBA'
    TTRG='TTRG'

@dataclass
class Shading(DataClassJSONMixin):
    version:str = "2.0.0"

    alpha:float = 1
    alphaCutoff:float = 0
    basecolor:BaseColor = field(default_factory=BaseColor)
    transmission:float = 0
    transmissionIOR:float = 1.45
    metallic:float = 0
    roughness:float = .85
    doubleSided:bool = False
    occlusion:float = 1

    emissiveColor: BaseColor =    field(default_factory=lambda: BaseColor(0,0,0))
    emissiveIntensity: float =    0.0
    clearcoatIntensity: float =   0.0
    clearcoatRoughness: float =   0.0
    clearcoatNormalScale: float = 0.0
    sheenColor: BaseColor =       field(default_factory=lambda: BaseColor(0,0,0))
    sheenIntensity: float =       0.0
    sheenRoughness: float =       0.65
    normalScale: float =          1.0
    specularIntensity: float =    0.0
    thicknessFactor: float =      0.0
    attenuationColor: BaseColor = field(default_factory=lambda: BaseColor(0,0,0))
    attenuationDistance: float =  0.0
    # TODO: make this work with material definition
    blendMode = "OPAQUE"


@dataclass
class CSV_ByDicts:
    row_dicts: list[dict] = field(default_factory=list)
    _quoting = csv.QUOTE_ALL

    @property
    def fieldnames(self):
        all_keys = set()
        for single_row_dict in self.row_dicts:
            all_keys.update(single_row_dict.keys())
        return tuple(all_keys)

    def add_row(self, row_dct: dict) -> None:
        self.row_dicts.append(row_dct)

    def write(self, file: Path):
        with file.open(mode="w", newline="") as output_csv:
            writer = csv.DictWriter(
                output_csv, fieldnames=self.fieldnames, quoting=self._quoting
            )
            writer.writeheader()
            writer.writerows(self.row_dicts)

@dataclass
class MaterialDefinition(CsvLine):
    def __init__(self) -> None:
        self.material_id: str = ""
        self.label_en: str = ""
        self.label_de: str = ""
        self.shading: Shading = Shading()
        self.thumbnail: str = ""

        self.diffuse_map = RoomleTextureImage()
        self.normal_map = RoomleTextureImage()
        self.orm_map = RoomleTextureImage()

        self.tag_ids_to_add: str = ''
        self.tag_ids_to_remove: str = ''
        self.description_en: str = ''
        self.active: int = 1
        self.active_from: str = ''
        self.active_till: str = ''
        self.visibility_status: str = ''
        self.sort: str = ''
        self.properties: str = ''

    def print_line(self):
        data = ([
            self.material_id,
            self.label_en,
            self.label_de,
            self.shading.to_json(),
            self.thumbnail,
        ] +
            self.diffuse_map.dump_list() +
            self.normal_map.dump_list() +
            self.orm_map.dump_list() +
            [
            self.tag_ids_to_add,
            self.tag_ids_to_remove,
            self.description_en,
            self.active,
            self.active_from,
            self.active_till,
            self.visibility_status,
            self.sort,
            self.properties,
        ]
        )
        return data



