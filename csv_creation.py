from __future__ import annotations
import csv

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class FieldNames:
    material_id = "material_id"
    label_en = "label_en"
    shading = "shading"
    thumbnail = "thumbnail"
    tag_ids_to_add = "tag_ids_to_add"
    tag_ids_to_remove = "tag_ids_to_remove"
    description_en = "description_en"
    active = "active"
    activeFrom = "activeFrom"
    activeTill = "activeTill"
    visibilityStatus = "visibilityStatus"
    sort = "sort"
    properties = "properties"

    # textures can be 0 to n
    tex_tileable = "tex{texture_number}_tileable"
    tex_image = "tex{texture_number}_image"
    tex_mapping = "tex{texture_number}_mapping"
    tex_mmwidth = "tex{texture_number}_mmwidth"
    tex_mmheight = "tex{texture_number}_mmheight"


class CsvFile:
    def __init__(self) -> None:
        self.materials: list[CsvMaterial] = []

    def add_material(self, material: CsvMaterial):
        self.materials.append(material)

    @property
    def fieldnames(self) -> list[str]:
        headers = []
        for data in self.lines:
            for key in data.keys():
                if key not in headers:
                    headers.append(key)
        return headers

    @property
    def lines(self) -> list[dict]:
        return [material.data for material in self.materials]

    def write(self, path='test-output.csv'):
        with open(path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)

            writer.writeheader()
            for line in self.lines:
                writer.writerow(line)


class CsvMaterial:
    def __init__(self) -> None:
        self.data = {
            FieldNames.material_id: "",
            FieldNames.label_en: "",
            FieldNames.shading: "",
            FieldNames.thumbnail: "",
            FieldNames.tag_ids_to_add: "",
            FieldNames.tag_ids_to_remove: "",
            FieldNames.description_en: "",
            FieldNames.active: "",
            FieldNames.activeFrom: "",
            FieldNames.activeTill: "",
            FieldNames.visibilityStatus: "",
            FieldNames.sort: "",
            FieldNames.properties: "",
        }
        self.textures = -1

    @property
    def material_id(self):
        return self.data[FieldNames.material_id]

    @material_id.setter
    def material_id(self, new_val: str):
        self.data[FieldNames.material_id] = new_val
        return self

    def _get_tex_field_names(self, index: int) -> list[str]:
        return list({
            "key_tex_tileable": FieldNames.tex_tileable.format(**{'texture_number': index}),
            "key_tex_image": FieldNames.tex_image.format(**{'texture_number': index}),
            "key_tex_mapping": FieldNames.tex_mapping.format(**{'texture_number': index}),
            "key_tex_mmwidth": FieldNames.tex_mmwidth.format(**{'texture_number': index}),
            "key_tex_mmheight": FieldNames.tex_mmheight.format(**{'texture_number': index}),
        }.values())

    def add_texture(self, tex_image: str, tex_tileable: bool = True,  tex_mapping: str = 'RGBA', tex_mmwidth: int = 1, tex_mmheight=1,):
        self.textures += 1
        (
            key_tex_tileable,
            key_tex_image,
            key_tex_mapping,
            key_tex_mmwidth,
            key_tex_mmheight
        ) = self._get_tex_field_names(self.textures)

        self.data[key_tex_tileable] = tex_tileable
        self.data[key_tex_image] = tex_image
        self.data[key_tex_mapping] = tex_mapping
        self.data[key_tex_mmwidth] = tex_mmwidth
        self.data[key_tex_mmheight] = tex_mmheight


if __name__ == '__main__':

    file = CsvFile()

    mat = CsvMaterial()
    mat.add_texture('img')
    mat.add_texture('kkk')
    mat.material_id = 'some-name'

    mat2 = CsvMaterial()
    mat2.material_id = uuid4().__str__()
    mat2.add_texture('kkk')


    file.add_material(mat)
    file.add_material(mat2)

    file.write()


pass
