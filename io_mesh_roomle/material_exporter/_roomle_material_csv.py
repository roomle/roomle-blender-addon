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

    emissiveColor: BaseColor =        field(default_factory=lambda: BaseColor(0,0,0))
    emissiveIntensity: float =    0.0
    clearcoatIntensity: float =   0.0
    clearcoatRoughness: float =   0.0
    clearcoatNormalScale: float = 0.0
    sheenColor: BaseColor =           field(default_factory=lambda: BaseColor(0,0,0))
    sheenIntensity: float =       0.0
    sheenRoughness: float =       0.65
    normalScale: float =          1.0
    specularIntensity: float =    0.0
    thicknessFactor: float =      0.0
    attenuationColor: BaseColor =     field(default_factory=lambda: BaseColor(0,0,0))
    attenuationDistance: float =  0.0


@dataclass
class CsvHeaders(CsvLine):
    ordered_labels = [
        "material_id",
        "label_en",
        "label_de",
        "shading",
        "thumbnail",
        "tex0_tileable",
        "tex0_image",
        "tex0_mapping",
        "tex0_mmwidth",
        "tex0_mmheight",
        "tex1_tileable",
        "tex1_image",
        "tex1_mapping",
        "tex1_mmwidth",
        "tex1_mmheight",
        "tex2_tileable",
        "tex2_image",
        "tex2_mapping",
        "tex2_mmwidth",
        "tex2_mmheight",
        "tag_ids_to_add",
        "tag_ids_to_remove",
        "description_en",
        "active",
        "activeFrom",
        "activeTill",
        "visibilityStatus",
        "sort",
        "properties",
    ]

    def print_line(self) -> List:
        return self.ordered_labels


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


class RoomleMaterialsCsv:

    lines: List[Union[CsvHeaders, MaterialDefinition]] = []

    def __init__(self) -> None:
        self.lines=[CsvHeaders()]

    def add_material_definition(self, definition: MaterialDefinition):
        self.lines.append(definition)

    def write(self, csv_path:Path):
        assert str(csv_path).lower().endswith('.csv')
        csv_path.parent.mkdir(exist_ok=True)
        arr = [x.print_line() for x in self.lines]
        with open(csv_path, 'w', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')
            csv_writer.writerows(arr)



