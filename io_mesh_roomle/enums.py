# fmt: off
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


@dataclass(frozen=True)
class TAG_CSV_COLS:
    TAG_ID: str =               'tag_id'
    LABEL_EN: str =             'label_en'
    PARENTS_TO_ADD: str =       'parent_tag_ids_to_add'
    COMPONENTS_TO_ADD: str =    'component_ids_to_add'
    MATERIALS_TO_ADD: str =     'material_ids_to_add'
    # COMPONENTS_TO_ADD: str =    'components_to_add'
    # MATERIALS_TO_ADD: str =     'materials_to_add'


@dataclass(frozen=True)
class COMP_CSV_COLS:
    COMPONENT_ID: str =         'component_id'
    LABEL_DE: str =             'label_de'
    DESCRIPTION_DE: str =       'description_de'
    LABEL_EN: str =             'label_en'
    DESCRIPTION_EN: str =       'description_en'
    LABEL_FR: str =             'label_fr'
    DESCRIPTION_FR: str =       'description_fr'
    LABEL_IT: str =             'label_it'
    DESCRIPTION_IT: str =       'description_it'
    LABEL_JA: str =             'label_ja'
    DESCRIPTION_JA: str =       'description_ja'
    LABEL_NL: str =             'label_nl'
    DESCRIPTION_NL: str =       'description_nl'
    LABEL_RU: str =             'label_ru'
    DESCRIPTION_RU: str =       'description_ru'
    LABEL_ZH: str =             'label_zh'
    DESCRIPTION_ZH: str =       'description_zh'
    ACTIVE: str =               'active'
    PERSPECTIVE_IMAGE: str =    'perspectiveImage'
    TYPE: str =                 'type'
    DETAIL_TYPE: str =          'detailType'
    SORT: str =                 'sort'
    LAYER: str =                'layer'
    TAG_IDS_TO_ADD: str =       'tag_ids_to_add'
    TAG_IDS_TO_REMOVE: str =    'tag_ids_to_remove'

    # not included inside the RuAd csv
    COMPONENT_DEFINITION: str = 'component_definition'
    VISIBILITY_STATUS: str =    'visibilityStatus'


@dataclass(frozen=True)
class ITEMS_CSV_COLS:
    ITEM_ID: str =              'item_id'
    LABEL_EN: str =             'label_en'
    DESCRIPTION_EN: str =       'description_en'
    TYPE: str =                 'type'
    DETAIL_TYPE: str =          'detailType'
    WIDTH: str =                'width'
    DEPTH: str =                'depth'
    HEIGHT: str =               'height'
    SORT: str =                 'sort'
    LAYER: str =                'layer'
    SCALEABLE: str =            'scaleable'
    FLIPABLE: str =             'flipable'
    COLORABLE: str =            'colorable'
    VISIBILITY_STATUS: str =    'visibilityStatus'
    MANUFACTURER_SKU: str =     'manufacturerSKU'
    TAG_IDS_TO_ADD: str =       'tag_ids_to_add'
    TAG_IDS_TO_REMOVE: str =    'tag_ids_to_remove'
    CONFIGURATION: str =        'configuration'


@dataclass(frozen=True)
class FILE_NAMES:
    META_JSON: str =            'meta.json'
    MATERIALS_ZIP: str =        'materials.zip'
    MESHES_ZIP: str =           'meshes.zip'
    COMPONENTS_ZIP: str =       'components.zip'
    ITEMS_CSV: str =            'items.csv'
    TAGS_CSV: str =             'tags.csv'
    MATERIALS_CSV: str =        'materials.csv'


@dataclass(frozen=True)
class META_JSON_FIELDS:
    TARGET_ID: str =            'target_id'
    MATERIALS: str =            'materials'
    MESHES: str =               'meshes'
    COMPONENTS: str =           'components'
    ITEMS: str =                'items'
    TAGS: str =                 'tags'

# fmt: on
