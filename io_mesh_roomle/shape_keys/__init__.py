"""support shape keys"""

from dataclasses import dataclass
import json
from pathlib import Path
from pprint import pprint
from typing import List
from unittest import result
import bpy
import bmesh
import bpy_types
from mathutils import Vector
from uuid import uuid4 as id
from hashlib import md5

_SLIDER_TEMPLATE = (Path(__file__).parent / 'parameter.json').read_text()


class SliderTemplate:
    src: str

    def __init__(self, id, name) -> None:
        self.src = _SLIDER_TEMPLATE
        self.id = id
        self.name = name

    def get(self):
        return self.src.replace(
            '{id}',
            self.id
        ).replace(
            '{name}',
            self.name
        )


@dataclass
class KEYS:
    key_name = "key_name"
    delta = "delta"
    slider = "slider_id"


def find_all_objs_with_shape_keys() -> List[bpy_types.Object]:
    results = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        if obj.data.shape_keys == None:
            continue
        if len(obj.data.shape_keys.key_blocks) < 1:
            continue
        results.append(obj)
    return results


class ShapeKeyDeltas:
    obj: bpy_types.Object
    shape_keys: List[bpy.types.ShapeKey]
    slider_ids: dict = {}

    key_values: List[float] = []

    deltas: dict = {}
    context = None

    def __init__(self, obj: bpy_types.Object, context) -> None:
        print(context.area)
        self.obj = obj
        self.context = context
        self.shape_keys = [
            key_block for key_block in obj.data.shape_keys.key_blocks]
        for key in self.shape_keys:
            print('⚙️', key.name)
            h = md5(str(key.name).encode('utf-8')).hexdigest()
            self.slider_ids[key.name] = f'id_{h}'
        print('🐵', self.slider_ids)
        self._store_reset_values()

    def _store_reset_values(self) -> None:
        keys = self.shape_keys
        for key in keys:
            self.key_values.append(key.value)

    def _zero_all_shape_keys(self):
        for key in self.shape_keys:
            key.value = 0

    def _reset_all_shape_keys(self):
        for key, value in zip(self.shape_keys, self.key_values):
            key.value = value

    def _calc_deltas(self, copied_object, shape_key_name):
        original_verts = self.obj.data.vertices
        check_verts = copied_object.data.vertices
        for i, (a, b) in enumerate(zip(original_verts, check_verts)):
            if b.co == a.co:
                continue
            if i not in self.deltas.keys():
                self.deltas[i] = []
            self.deltas[i].append({
                KEYS.delta: b.co-a.co,
                KEYS.key_name: shape_key_name,
                KEYS.slider: self.slider_ids[shape_key_name]
            })

    def _all_deltas(self):
        key_delta_results = []
        self._zero_all_shape_keys()

        for shape_key in self.shape_keys[1:]:
            shape_key.value = 1

            temp_obj = self.get_modified_mesh(self.obj, cage=True)
            self._calc_deltas(temp_obj, shape_key.name)
            self._zero_all_shape_keys()
        self._reset_all_shape_keys()
        pprint(self.deltas)

    def get_modified_mesh(self, obx, cage=False):
        ob = obx.copy()

        bm = bmesh.new()
        bm.from_object(
            ob,
            self.context.evaluated_depsgraph_get(),
            cage=cage,
        )

        # bm.transform(ob.matrix_world)
        me = bpy.data.meshes.new("Deformed")
        bm.to_mesh(me)

        ob.data = me
        return ob

    def print(self):
        for i, v in enumerate(self.obj.data.vertices):
            x, y, z = v.co
            s_x = f'{x}'
            s_y = f'{y}'
            s_z = f'{z}'
            if i in self.deltas:
                for e in self.deltas[i]:
                    name = e[KEYS.key_name]
                    dx, dy, dz = e[KEYS.delta]
                    s_x += f'+{dx}*{name}'
                    s_y += f'+{dy}*{name}'
                    s_z += f'+{dz}*{name}'
            print(f'{{{s_x},{s_y},{s_z}\}}')


def does_have_shape_key(obj):
    if obj.type != 'MESH':
        return False
    if obj.data.shape_keys == None:
        return False
    if len(obj.data.shape_keys.key_blocks) < 1:
        return False
    return True


def process_all_shapekeys(objs: List[bpy_types.Object]) -> List[bpy_types.Object]:

    for org in objs:
        all_keys: ShapeKeyDeltas = ShapeKeyDeltas(org)
        all_keys._all_deltas()
        all_keys.print()
        # context.collection.objects.link(ob)


def MAIN():
    objs = find_all_objs_with_shape_keys()
    process_all_shapekeys(objs)


if __name__ == "__main__":
    print('🚀', '='*40)
    MAIN()
