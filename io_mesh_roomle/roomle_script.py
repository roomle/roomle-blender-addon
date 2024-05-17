# -----------------------------------------------------------------------
#
#  Copyright 2019 Roomle GmbH. All Rights Reserved.
#
#  This Software is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
#
#  NOTICE: All information contained herein is, and remains
#  the property of Roomle. The intellectual and technical concepts contained
#  herein are proprietary to Roomle and are protected by copyright law.
#  Dissemination of this information or reproduction of this material
#  is strictly forbidden unless prior written permission is obtained
#  from Roomle.
# -----------------------------------------------------------------------

from __future__ import annotations
from binhex import hexbin
import csv
from hashlib import md5, sha256
import json
from pathlib import Path

from typing import Any, Iterable
from uuid import uuid4
import bpy
import bmesh

import os
import re
import subprocess

from dataclasses import dataclass
from decimal import Decimal
from math import degrees, floor, log10
from copy import deepcopy

from mathutils import Vector

from bpy_extras.io_utils import (
    axis_conversion,
)

from io_mesh_roomle import arguments, material_exporter
from io_mesh_roomle.csv_handler import CSV_Writer
from io_mesh_roomle.csv_handler import _CSV_DictHandler
from io_mesh_roomle.enums import FILE_NAMES, TAG_CSV_COLS


@dataclass
class VertexVariant:
    index: int
    loop_index: int
    #normal: Vector


def get_valid_name(name):
    return re.sub('[^0-9a-zA-Z_]+', '_', name)


def isZero(self, precision=0):
    q = Decimal(10) ** -precision  # 2 precision --> '0.01'
    if isinstance(self, float):
        return Decimal(self).quantize(q).normalize() == 0
    for f in self:
        if Decimal(f).quantize(q).normalize() != 0:
            return False
    return True


def floatFormat(value, precision=0):
    """
    Converts a float to a string. Rounds to a certain precision and removed trailing zeros.
    """
    q = Decimal(10) ** -precision      # 2 precision --> '0.01'
    d = Decimal(value)
    result = '{:f}'.format(d.quantize(q).normalize())
    return '0' if result == '-0' else result


def is_child(parent, child):
    for c in parent.children:
        if c == child:
            return True
        if is_child(c, child):
            return True
    return False


def sort_tri(tri):
    min_v = None
    min_i = None
    for i, v in enumerate(tri):
        if min_i is None or v < min_v:
            min_i = i
            min_v = v
    return tri[min_i:] + tri[:min_i]


def sort_indices_by_first(inds):
    tris = [tuple(inds[i:i+3]) for i in range(0, len(inds), 3)]
    tris = list(map(lambda x: sort_tri(x), tris))
    tris.sort()
    return [i for tri in tris for i in tri]


def indices_from_mesh(ob, use_mesh_modifiers=False):

    # get the editmode data
    ob.update_from_editmode()

    # get the modifiers
    try:
        mesh = ob.to_mesh(
            depsgraph=bpy.context.evaluated_depsgraph_get(),
        )
    except RuntimeError:
        raise StopIteration

    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Remove loose vertices (not attached to a face)
    loose_verts = list(filter(lambda x: len(x.link_faces) <= 0, bm.verts))
    bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(mesh)
    bm.free()

    mesh.calc_normals()
    mesh.calc_loop_triangles()
    mesh.calc_normals_split()

    uv_layer_index = mesh.uv_layers.active_index
    uv_layer = mesh.uv_layers[uv_layer_index] if uv_layer_index >= 0 else None

    vertices = []
    normals = []
    indices = []

    for v in mesh.vertices:
        vertices.append(v.co)
        # for some weird reason I have to invert the normal here.
        # dunno why
        normals.append(v.normal * -1)

    # Vertex variants have to be created if points/triangles share a vertex (positional data),
    # but have different UVs (or normals or color in the future)
    create_vertex_variants = uv_layer is not None

    split_uvs = False
    uvs = None

    if create_vertex_variants:
        # key: vertex index
        vertex_variants = {}

        # Init UVs with minimum length (=number of vertices)
        uvs = [None] * len(mesh.vertices)

        for triangle in mesh.loop_triangles:
            for orig_index, loop_index in zip(triangle.vertices, triangle.loops):
                if orig_index in vertex_variants:
                    vv = None
                    for vertex_variant in vertex_variants[orig_index]:
                        if (
                            loop_index == vertex_variant.loop_index
                            or uv_layer.data[loop_index].uv == uv_layer.data[vertex_variant.loop_index].uv
                        ):
                            # Identical: re-use vertex variant
                            vv = vertex_variant
                            loop_index = vv.loop_index
                            indices.append(vv.index)
                            break

                    if not vv:
                        # New vertex variant: create a copy
                        split_uvs = True

                        assert len(vertices) == len(
                            uvs), 'vert/uv array out of sync'

                        v_index = len(vertices)
                        vertices.append(mesh.vertices[orig_index].co)
                        indices.append(v_index)
                        uvs.append(uv_layer.data[loop_index].uv)

                        vv = VertexVariant(v_index, loop_index)
                        vertex_variants[orig_index].append(vv)
                else:
                    indices.append(orig_index)
                    vv = VertexVariant(orig_index, loop_index)
                    vertex_variants[orig_index] = [vv]
                    uvs[orig_index] = uv_layer.data[loop_index].uv

    else:
        # No vertex variants
        for triangle in mesh.loop_triangles:
            indices += triangle.vertices[:]

    # flipping triangle order
    sorted_indices = []
    for i in range(len(indices)):
        m = i % 3
        sorted_i = i-1 if m == 2 else i+m
        # i sequence is..........0,1,2,3,4,5,...
        # sorted_i sequence is ..0,2,1,3,5,4,...
        sorted_indices.append(indices[sorted_i])
    indices = sorted_indices

    # Create deep copies of output so we safely can remove the temporary mesh
    vertices = deepcopy(vertices)
    indices = deepcopy(indices)
    uvs = None if uvs is None else deepcopy(uvs)
    normals = deepcopy(normals)

    return vertices, indices, uvs, normals, split_uvs


def create_mesh_command(object, global_matrix, addon_args: arguments.ArgsStore, use_mesh_modifiers=True, scale=None, rotation=None):

    debug = addon_args.debug

    command = '/* Object:{} Mesh:{} */\n'.format(object.name, object.data.name)
    command += 'AddMesh('
    export_normals = addon_args.export_normals
    apply_rotation = addon_args.apply_rotations and rotation

    vertices, indices, uvs, normals, split_uvs = indices_from_mesh(
        object, use_mesh_modifiers)

    export_normals |= split_uvs

    if debug:
        command += '\n// Vertex positions:\n'
    command += 'Vector3f['
    for i, vertex in enumerate(vertices):
        if i > 0:
            command += ','
        if debug:
            command += '\n'
        v = vertex.copy()
        if scale:
            v.x *= scale.x
            v.y *= scale.y
            v.z *= scale.z
        if apply_rotation:
            v = rotation @ v

        v = global_matrix @ v

        command += '{{{0},{1},{2}}}'.format(floatFormat(v.x, 1),
                                            floatFormat(v.y, 1), floatFormat(v.z, 1))
    if debug:
        command += '\n'
    command += '],'

    if debug:
        indices = sort_indices_by_first(indices)
        command += '\n// Indices:\n['
        for i, index in enumerate(indices):
            if i % 3 == 0:
                command += '\n'
            if i != 0:
                command += ','
            command += str(index)
        command += '\n]'
    else:
        command += '['
        command += ','.join(map(str, indices))
        command += ']'

    if uvs:

        assert len(vertices) == len(
            uvs), 'vertex count does not match UV count {}!={}'.format(len(vertices), len(uvs))
        maxvalue = 1
        for p in uvs:
            maxvalue = max(maxvalue, *[abs(x) for x in p])

        uv_prec = max(0, addon_args.uv_float_precision -
                      floor(log10(abs(maxvalue))))

        if debug:
            command += '\n// UVs:\n'
        command += ',Vector2f['
        if debug:
            for i, p in enumerate(uvs):
                if i != 0:
                    command += ','
                if debug:
                    command += '\n'
                command += '{{{0},{1}}}'.format(floatFormat(
                    p[0], uv_prec), floatFormat(p[1], uv_prec))
        else:
            command += ','.join('{{{0},{1}}}'.format(floatFormat(
                p[0], uv_prec), floatFormat(p[1], uv_prec)) for p in uvs)

        command += '\n]' if debug else ']'

    if export_normals:
        norm_prec = addon_args.normal_float_precision

        if debug:
            command += '\n// Normals:\n'
            command += ',Vector3f['
            for i, n in enumerate(normals):
                if i != 0:
                    command += ','
                if debug:
                    command += '\n'
                command += '{{{0},{1},{2}}}'.format(floatFormat(n.x, norm_prec), floatFormat(
                    n.y, norm_prec), floatFormat(n.z, norm_prec))
            command += '\n]'
        else:
            command += ',Vector3f['
            command += ','.join('{{{0},{1},{2}}}'.format(floatFormat(n.x, norm_prec),
                                floatFormat(n.y, norm_prec), floatFormat(n.z, norm_prec)) for n in normals)
            command += ']'

    command += ');\n'
    return command


def get_object_bounding_box(object):
    corners = object.bound_box

    vals = [c[0] for c in corners]
    xmin = min(vals)
    xmax = max(vals)

    vals = [c[1] for c in corners]
    ymin = min(vals)
    ymax = max(vals)

    vals = [c[2] for c in corners]
    zmin = min(vals)
    zmax = max(vals)

    dim = Vector((xmax-xmin, ymax-ymin, zmax-zmin))
    center = Vector((xmax+xmin, ymax+ymin, zmax+zmin))*0.5
    return dim, center


def create_extern_mesh_command(
    preferences,
    extern_mesh_dir,
    object,
    global_matrix,
    addon_args: arguments.ArgsStore,
    use_mesh_modifiers=True,
    scale=None,
    rotation=None,
):
    '''
    Save external meshes and convert them to
    corto if a corto exe is found
    '''

    apply_rotation = addon_args.apply_rotations and rotation
    name = object.name if (scale or apply_rotation) else object.data.name
    name = name.replace(' ','_')

    mesh = object.to_mesh(
        depsgraph=bpy.context.evaluated_depsgraph_get(),
    )

    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(mesh)

    tri_mesh = bpy.data.meshes.new(name)
    tri_mesh.use_auto_smooth = mesh.use_auto_smooth

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(tri_mesh)
    bm.free()

    if not os.path.isdir(extern_mesh_dir):
        os.makedirs(extern_mesh_dir)

    # TODO: RML-7624 change variable name
    script_name = addon_args.component_id

    scene = bpy.context.scene

    bpy.ops.object.select_all(action='DESELECT')

    # create temporary object with same mesh data but without transformation
    tmp = bpy.data.objects.new('tmp_'+name, tri_mesh)

    triangulate_mod = tmp.modifiers.new('Triangulate', 'TRIANGULATE')
    triangulate_mod.keep_custom_normals = mesh.has_custom_normals

    # put the object into the scene (link)
    scene.collection.objects.link(tmp)

    if scale:
        tmp.scale = scale
    if apply_rotation:
        tmp.rotation_mode = 'QUATERNION'
        tmp.rotation_quaternion = rotation

    # set as the active object in the scene
    bpy.context.view_layer.objects.active = tmp
    tmp.select_set(True)  # select object

    # Apply transform (necessary to have correct boundings box)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    filepath = os.path.join(extern_mesh_dir, f'{script_name}_{name}')

    filepath += '.obj'
    bpy.ops.export_scene.obj(
        filepath=filepath,
        check_existing=False,
        use_selection=True,
        use_mesh_modifiers=use_mesh_modifiers,
        use_normals=addon_args.export_normals,
        global_scale=1000,
        use_uvs=True,
        use_blen_objects=False,
        use_materials=False,
        axis_forward='Y',
        axis_up='Z',
    )

    dim, center = get_object_bounding_box(tmp)

    bpy.data.objects.remove(tmp)  # remove temporary object
    bpy.data.meshes.remove(tri_mesh)

    if scale:
        dim.x *= scale.x
        dim.y *= scale.y
        dim.z *= scale.z

        center.x *= scale.x
        center.y *= scale.y
        center.z *= scale.z

    # Convert to Roomle Script space
    dim *= 1000
    center *= 1000
    center.y *= -1
    bb_origin = center - (dim*0.5)
    dim_str = (floatFormat(dim.x, 1), floatFormat(
        dim.y, 1), floatFormat(dim.z, 1))
    center_str = (floatFormat(bb_origin.x, 1), floatFormat(
        bb_origin.y, 1), floatFormat(bb_origin.z, 1))

    # TODO: RML-7624 refactor
    script = 'AddExternalMesh(\'{}:{}_{}\',Vector3f{{{},{},{}}},Vector3f{{{},{},{}}});\n'.format(
        addon_args.catalog_id,
        script_name,
        name,
        *dim_str,
        *center_str
    )

    if addon_args.use_corto and preferences.corto_exe and os.path.isfile(preferences.corto_exe):
        try:
            corto_process = subprocess.Popen(
                [preferences.corto_exe, '-v 12 -n 9 -u 10 -N delta', filepath])
            if corto_process.wait() != 0:
                raise Exception('corto error')
        except Exception as e:
            print(e)
            pass
        else:
            os.remove(filepath)
        print(preferences.corto_exe)

    return script


def create_transform_commands(
    object,
    global_matrix,
    parent_scale=None,
    apply_rotation=True,
    parent_rotation=None
):
    command = ''
    pos = object.matrix_local.translation.copy()

    # rotation
    if not apply_rotation:
        rot = object.matrix_local.to_euler()
        x, y, z = map(degrees, (-rot.x, rot.y, -rot.z))
        rotation_precision = 2
        if not isZero(x, rotation_precision):
            command += "RotateMatrixBy(Vector3f{{1,0,0}},Vector3f{{0,0,0}},{});\n".format(
                floatFormat(x, rotation_precision))
        if not isZero(y, rotation_precision):
            command += "RotateMatrixBy(Vector3f{{0,1,0}},Vector3f{{0,0,0}},{});\n".format(
                floatFormat(y, rotation_precision))
        if not isZero(z, rotation_precision):
            command += "RotateMatrixBy(Vector3f{{0,0,1}},Vector3f{{0,0,0}},{});\n".format(
                floatFormat(z, rotation_precision))

    # translation
    if parent_scale:
        pos.x = pos.x * parent_scale.x
        pos.y = pos.y * parent_scale.y
        pos.z = pos.z * parent_scale.z

    if apply_rotation and parent_rotation:
        pos = parent_rotation @ pos

    pos = pos @ global_matrix

    if not isZero(pos, precision=1):
        command += "MoveMatrixBy(Vector3f{{{0},{1},{2}}});\n".format(
            floatFormat(pos.x, 1), floatFormat(pos.y, 1), floatFormat(pos.z, 1))

    return command


def create_object_commands(
    preferences,
    object,
    object_list,
    extern_mesh_dir,
    global_matrix,
    addon_args: arguments.ArgsStore,
    parent_scale=None,
    parent_rotation=None,
    apply_transform=False,
):
    '''
    Create all necessary commands for one object
    this function gets called by the loop over all objects
    '''

    # TODO: separate out the mesh creation for better readability

    command = ''

    empty = True

    mesh = ''
    material = ''

    scale = object.matrix_world.to_scale()
    if scale.x == 1 and scale.y == 1 and scale.z == 1:
        scale = None

    apply_rotation = addon_args.apply_rotations
    rotation = None
    if apply_rotation:
        rotation = object.matrix_world.to_quaternion()
        if rotation.x == 0 and rotation.y == 0 and rotation.z == 0 and rotation.w == 1:
            rotation = None

    if object_list == None or (object in object_list):
        # Mesh
        if object.data and isinstance(object.data, bpy.types.Mesh):
            empty = False

            method = addon_args.mesh_export_option

            extern = (method == 'EXTERNAL') or (
                method == 'AUTO' and len(object.data.vertices) > 100)

            if extern:
                mesh = create_extern_mesh_command(
                    preferences,
                    extern_mesh_dir,
                    object,
                    global_matrix,
                    scale=scale,
                    rotation=rotation,
                    addon_args=addon_args
                )
            else:
                mesh = create_mesh_command(
                    object, global_matrix, scale=scale, rotation=rotation, addon_args=addon_args)

            # Material
            material = ''
            if object.material_slots:
                material_name = get_valid_name(object.material_slots[0].name)
                # TODO: 5959 create material definition
                material = f"SetObjSurface('{material_name}');\n"

    # Children
    childCommands = ''
    if len(object.children) > 0:
        for child in object.children:
            if child:
                childCommands += create_object_commands(
                    preferences,
                    child,
                    object_list,
                    extern_mesh_dir,
                    global_matrix,
                    addon_args=addon_args,
                    parent_scale=scale,
                    parent_rotation=rotation,
                )

    hasChildren = bool(childCommands)
    empty = empty and not hasChildren

    if hasChildren:
        command += "BeginObjGroup('{}');\n".format(get_valid_name(object.name))

    command += mesh
    command += material

    if hasChildren:
        command += childCommands
        command += "EndObjGroup();\n"

    # Transform
    if not apply_transform and not empty:
        command += create_transform_commands(
            object,
            global_matrix,
            parent_scale=parent_scale,
            apply_rotation=apply_rotation,
            parent_rotation=parent_rotation
        )

    return command

@dataclass
class MaterialParameterTag:
    """Handles the materials within the roomle script"""

    catalog_id: str 
    component_id: str
    material_id: str

    _counter = 0

    def __post_init__(self) -> None:
        self.num = self._get_number()

    @classmethod
    def _get_number(cls):
        cls._counter += 1
        return cls._counter

    @property
    def key(self) -> str:
        return f'material_{self.num:03}'

    @property
    def label_en(self) -> str:
        ma = self.material_id.replace('_',' ')
        return f'{ma} ({self.component_id})'
    
    @property
    def script_label_en(self) -> str:
        """this label is shown above the material selection in the configurator"""
        ma = self.material_id.replace('_',' ')
        return f'{ma}'
    
    @property
    def material_ext_id(self) -> str:
        return f'{self.catalog_id}:{self.component_id}_{self.material_id}'

    @property
    def tag_id(self) -> str:
        # return md5(self.material_ext_id.encode('utf-8')).hexdigest()
        return f'{self.component_id}_{self.material_id}_{self.catalog_id}'
        # return f'{self.component_id}_{self.material_id}'

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "type": "Material",
            "labels": {
                "en": self.script_label_en
            },
            "defaultValue": self.material_ext_id,
            "validGroups": [
                self.tag_id
            ]
        }
    @property
    def csv_row(self) -> dict:
        return {
                TAG_CSV_COLS.TAG_ID: self.tag_id,
                TAG_CSV_COLS.LABEL_EN: self.script_label_en,
                TAG_CSV_COLS.MATERIALS_TO_ADD: [self.material_ext_id]
                }


class ComponentDefinition:

    def __init__(self, catalog_id: str, component_id: str, geometry_script: str,) -> None:

        self.catalog_id: str = catalog_id
        self.component_id: str = component_id
        self.input_geometry_script: str = geometry_script

        self._place_holder: str = '::GEO-SCRIPT::'

        self.mod_geo_script: str
        self.material_parameters: list[MaterialParameterTag]
        self.mod_geo_script, self.material_parameters = self.process_geometry_script(geometry_script, self.component_id,self.catalog_id)

        pass

    @property
    def external_id(self) -> str:
        return f'{self.catalog_id}:{self.component_id}'

    @property
    def material_parameters_as_dict(self) -> list[dict]:
        return [mat_para.as_dict for mat_para in self.material_parameters]

    @property
    def component_definition(self) -> str:
        # TODO: decide how to handle line breaks within a geometry script
        with_line_breaks = False
        if with_line_breaks:
            comp_json = {
                "id": self.external_id,
                "parameters": self.material_parameters_as_dict,
                "geometry": self._place_holder
            }
            return (
                json.dumps(comp_json, indent=4)
                .replace(self._place_holder, self.mod_geo_script)
            )
        else:
            comp_json = {
                "id": self.external_id,
                "parameters": self.material_parameters_as_dict,
                "geometry": self.mod_geo_script
            }
            return json.dumps(comp_json, indent=4)
    @staticmethod
    def process_geometry_script(geometry_script, component_id, catalog_id) -> tuple[str, list[MaterialParameterTag]]:
        """extract material statements from given roomle script

        Args:
            geometry_script (str): roomle geomrtry script

        Returns:
            tuple[str,list[MaterialParameter]]: modified geometry script, List[material parameters]
        """

        modified_geometry_script = []
        material_parameters = []

        for line in geometry_script.split('\n'):
            if not line.startswith('SetObjSurface'):
                modified_geometry_script.append(line)
                continue
            before, material_id, after = line.split("'")
            material_id= material_id.split(':')[-1]
            new_mat_param = MaterialParameterTag(catalog_id,component_id,material_id)
            material_parameters.append(new_mat_param)

            modified_geometry_script.append(
                f"{before}{new_mat_param.key}{after}")

        return '\n'.join(modified_geometry_script), material_parameters


def create_objects_commands(preferences, objects, object_list, extern_mesh_dir, global_matrix, addon_args: arguments.ArgsStore, ):
    '''
    Create the Roomle Script command
    iterate over all objects and pass them
    to the create_object_commands
    '''
    command = ''
    if addon_args.debug:
        command += '/* Roomle script DEBUG */\n'
    else:
        from . import bl_info
        command += '/* Roomle script (Roomle Blender addon version {}) */\n'.format(
            '.'.join([str(x) for x in bl_info['version']]))

    for object in objects:
        if object:
            command += create_object_commands(preferences, object, object_list,
                                              extern_mesh_dir, global_matrix, addon_args=addon_args)
    return command.rstrip()

# def write_roomle_script( operator, preferences, context, filepath, global_matrix, **args ):


def write_roomle_script(operator, preferences, context, global_matrix, addon_args: arguments.ArgsStore):
    """
    Write a roomle script file from faces,

    filepath
       output filepath

    faces
       iterable of tuple of 3 vertex, vertex is tuple of 3 coordinates as float
    """
    try:

        scene = bpy.context.scene

        root_objects = []
        for obj in scene.objects:
            if not obj.parent:
                root_objects.append(obj)

        object_list = bpy.context.selected_objects if addon_args.use_selection else bpy.context.visible_objects

        extern_mesh_dir = addon_args.export_dir / 'meshes'

        geometry_script = create_objects_commands(
            preferences, root_objects, object_list, extern_mesh_dir, global_matrix, addon_args)
        if not bool(geometry_script):
            raise Exception(
                'Empty export! Make sure you have meshes selected.')
        else:

            # region #*======================= [ 🔶  GENERATE COMPONENT DEFINITION FROM GEO SCRIPT 🔶 ] ===============================

            comp_def = ComponentDefinition(
                catalog_id=addon_args.catalog_id,
                component_id=addon_args.component_id,
                geometry_script=geometry_script
            )
                
            with open(addon_args.components_dir / addon_args.component_definition_file_name, 'w') as data:
                data.write(comp_def.component_definition)

            # endregio

            # region #*======================= [ 🔶  WRITE TAGS.CSV 🔶 ] ===============================
            
            
            dict_csv_handler = _CSV_DictHandler()
            dict_csv_handler.add_row({
                TAG_CSV_COLS.TAG_ID: addon_args.component_tag,
                TAG_CSV_COLS.LABEL_EN: addon_args.component_tag_label_en,
                # TAG_CSV_COLS.PARENTS_TO_ADD: addon_args.catalog_root_tag,
                TAG_CSV_COLS.COMPONENTS_TO_ADD: addon_args.component_ext_id
                })
            
            #* We have to track the created tag ids in order to prevent duplication
            track_ids = []

            for mat in comp_def.material_parameters:
                row_dict = mat.csv_row
                curr_id = row_dict[TAG_CSV_COLS.TAG_ID]
                if curr_id in track_ids:
                    continue
                else:
                    track_ids.append(curr_id)
                row_dict[TAG_CSV_COLS.PARENTS_TO_ADD] = (addon_args.component_tag,)
                dict_csv_handler.add_row(row_dict)

            dict_csv_handler.write(addon_args.export_dir / FILE_NAMES.TAGS_CSV)

            # endregion

    except Exception as e:
        import traceback
        print('Exception', e)
        x = traceback.format_exc()
        print(x)
