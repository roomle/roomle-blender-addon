# full list: https://docs.blender.org/api/current/bpy_types_enum_items/image_type_items.html#rna-enum-image-type-items

from dataclasses import dataclass


SUPPORTED_TEXTURE_FILE_FORMATS = {
"BMP": ".bmp",
"PNG": ".png",
"JPEG": ".jpg",
"JPEG2000": ".jpg2",
"WEBP": ".webp",
"TIFF": ".tif",
}

@dataclass
class TAG_CSV_COLS:
    TAG_ID:str = 'tag_id'
    LABEL_EN:str = 'label_en'
    PARENTS_TO_ADD: str = 'parents_to_add'
    COMPONENTS_TO_ADD:str = 'components_to_add'
    MATERIALS_TO_ADD:str = 'materials_to_add'
