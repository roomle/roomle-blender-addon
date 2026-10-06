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

import bpy
import bmesh

import os
import re
import shutil
import subprocess
import inspect

from dataclasses import dataclass
from decimal import Decimal
from math import degrees,floor,log10
from copy import deepcopy

from mathutils import Vector

from bpy_extras.io_utils import (
        axis_conversion,
        )

from .scene_handler import get_export_name

RLCS_MESH_FILE_NAME = 'crt_50.crt'

@dataclass
class VertexVariant:
    index: int
    loop_index: int
    #normal: Vector

def getValidName(name):
    return re.sub('[^0-9a-zA-Z:_]+', '', name)

def isZero(self, precision=0):
    q = Decimal(10) ** -precision # 2 precision --> '0.01'
    if isinstance(self, float):
        return Decimal(self).quantize(q).normalize()==0
    for f in self:
        if Decimal(f).quantize(q).normalize()!=0:
            return False
    return True

def floatFormat( value, precision=0 ):
    """
    Converts a float to a string. Rounds to a certain precision and removed trailing zeros.
    """
    q = Decimal(10) ** -precision      # 2 precision --> '0.01'
    d = Decimal(value)
    result = '{:f}'.format(d.quantize(q).normalize())
    return '0' if result == '-0' else result

def is_child(parent, child):
    for c in parent.children:
        if c==child:
            return True
        if is_child(c,child):
            return True
    return False

def sort_tri(tri):
    min_v = None
    min_i = None
    for i,v in enumerate(tri):
        if min_i is None or v<min_v:
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
    bmesh.ops.delete(bm,geom=loose_verts,context='VERTS')

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(mesh)
    bm.free()

    if hasattr(mesh, 'calc_normals'):
        mesh.calc_normals()
    mesh.calc_loop_triangles()
    if hasattr(mesh, 'calc_normals_split'):
        mesh.calc_normals_split()
    
    uv_layer_index = mesh.uv_layers.active_index
    uv_layer = mesh.uv_layers[uv_layer_index] if uv_layer_index>=0 else None

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
            for orig_index,loop_index in zip(triangle.vertices,triangle.loops):
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

                        assert len(vertices)==len(uvs), 'vert/uv array out of sync'
                        
                        v_index = len(vertices)
                        vertices.append(mesh.vertices[orig_index].co)
                        indices.append(v_index)
                        uvs.append(uv_layer.data[loop_index].uv)

                        vv=VertexVariant(v_index,loop_index)
                        vertex_variants[orig_index].append(vv)
                else:
                    indices.append(orig_index)
                    vv = VertexVariant(orig_index,loop_index)
                    vertex_variants[orig_index] = [vv]
                    uvs[orig_index] = uv_layer.data[loop_index].uv
        
    else:
        # No vertex variants
        for triangle in mesh.loop_triangles:
            indices += triangle.vertices[:]

    # flipping triangle order
    sorted_indices=[]
    for i in range(len(indices)):
        m=i%3
        sorted_i = i-1 if m==2 else i+m
        # i sequence is..........0,1,2,3,4,5,...
        # sorted_i sequence is ..0,2,1,3,5,4,...
        sorted_indices.append( indices[sorted_i] )
    indices = sorted_indices
    
    # Create deep copies of output so we safely can remove the temporary mesh
    vertices = deepcopy(vertices)
    indices = deepcopy(indices)
    uvs = None if uvs is None else deepcopy(uvs)
    normals = deepcopy(normals)

    return vertices, indices, uvs, normals, split_uvs
        
def create_mesh_command( object, global_matrix, use_mesh_modifiers = True, scale=None, rotation=None, **args ):
    
    debug = args['debug']

    command = '/* Object:{} Mesh:{} */\n'.format(get_export_name(object),get_export_name(object.data))
    command += 'AddMesh('
    export_normals = args['export_normals']
    apply_rotation = args['apply_rotations'] and rotation

    vertices, indices, uvs, normals, split_uvs = indices_from_mesh(object,use_mesh_modifiers)
    
    export_normals |= split_uvs

    if debug:
        command += '\n// Vertex positions:\n'
    command += 'Vector3f['
    for i,vertex in enumerate(vertices):
        if i>0:
            command += ','
        if debug:
            command += '\n'
        v=vertex.copy()
        if scale:
            v.x *= scale.x
            v.y *= scale.y
            v.z *= scale.z
        if apply_rotation:
            v = rotation @ v

        v = global_matrix @ v

        command +='{{{0},{1},{2}}}'.format( floatFormat(v.x,1), floatFormat(v.y,1), floatFormat(v.z,1) )
    if debug:
        command += '\n'
    command += '],'
    
    if debug:
        indices= sort_indices_by_first(indices)
        command += '\n// Indices:\n['
        for i,index in enumerate(indices):
            if i%3==0:
                command += '\n'
            if i!=0:
                command += ','
            command += str(index)
        command += '\n]'
    else:
        command += '['
        command += ','.join(map(str,indices))
        command += ']'

    if uvs:

        assert len(vertices) == len(uvs), 'vertex count does not match UV count {}!={}'.format(len(vertices),len(uvs))
        maxvalue = 1
        for p in uvs:
            maxvalue = max(maxvalue, *[abs(x) for x in p] )

        uv_prec = max( 0, args['uv_float_precision'] - floor(log10(abs(maxvalue))))

        if debug:
            command += '\n// UVs:\n'
        command+=',Vector2f['
        if debug:
            for i,p in enumerate(uvs):
                if i!=0:
                    command += ','
                if debug:
                    command += '\n'
                command += '{{{0},{1}}}'.format( floatFormat(p[0],uv_prec), floatFormat(p[1],uv_prec) )
        else:
            command += ','.join( '{{{0},{1}}}'.format( floatFormat(p[0],uv_prec), floatFormat(p[1],uv_prec) ) for p in uvs)

        command+= '\n]' if debug else ']'

    if export_normals:
        norm_prec = args['normal_float_precision']

        if debug:
            command += '\n// Normals:\n'
            command += ',Vector3f['
            for i,n in enumerate(normals):
                if i!=0:
                    command += ','
                if debug:
                    command += '\n'
                command += '{{{0},{1},{2}}}'.format( floatFormat(n.x,norm_prec), floatFormat(n.y,norm_prec), floatFormat(n.z,norm_prec) )
            command += '\n]'
        else:
            command += ',Vector3f['
            command += ','.join( '{{{0},{1},{2}}}'.format( floatFormat(n.x,norm_prec), floatFormat(n.y,norm_prec), floatFormat(n.z,norm_prec) ) for n in normals)
            command += ']'
        
    command+=');\n'
    return command

def get_object_bounding_box( object ):
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

    dim = Vector(( xmax-xmin, ymax-ymin, zmax-zmin ))
    center = Vector(( xmax+xmin, ymax+ymin, zmax+zmin ))*0.5
    return dim,center

def create_extern_mesh_command(
    preferences,
    extern_mesh_dir,
    object,
    global_matrix,
    use_mesh_modifiers = True,
    scale=None,
    rotation=None,
    **args
):
    '''
    Save external meshes and convert them to
    corto if a corto exe is found
    '''

    apply_rotation = args['apply_rotations'] and rotation
    name = get_export_name(object) if (scale or apply_rotation) else get_export_name(object.data)

    mesh = object.to_mesh(
        depsgraph=bpy.context.evaluated_depsgraph_get(),
    )

    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(mesh)

    tri_mesh = bpy.data.meshes.new(name)
    if hasattr(tri_mesh, 'use_auto_smooth') and hasattr(mesh, 'use_auto_smooth'):
        tri_mesh.use_auto_smooth = mesh.use_auto_smooth

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(tri_mesh)
    bm.free()

    script_name = os.path.basename(extern_mesh_dir)
    mesh_name = f'{script_name}_{name}' if args['use_file_name_prefix'] else name

    if args['folder_layout'] == 'RLCS':
        # <file name>/meshes/<mesh id>/crt_50.crt as served by the Rubens Local Content Server
        mesh_dir = os.path.join(extern_mesh_dir, 'meshes', mesh_name)
        crt_filepath = os.path.join(mesh_dir, RLCS_MESH_FILE_NAME)
    else:
        mesh_dir = extern_mesh_dir
        crt_filepath = os.path.join(mesh_dir, mesh_name + '.crt')

    os.makedirs(mesh_dir, exist_ok=True)
    # a corto file of a previous export must not survive a failed compression
    if os.path.isfile(crt_filepath):
        os.remove(crt_filepath)

    scene = bpy.context.scene
    
    bpy.ops.object.select_all(action='DESELECT')

    tmp = bpy.data.objects.new('tmp_'+name, tri_mesh) # create temporary object with same mesh data but without transformation
    
    triangulate_mod = tmp.modifiers.new('Triangulate','TRIANGULATE')
    triangulate_mod.keep_custom_normals = mesh.has_custom_normals

    # put the object into the scene (link)
    scene.collection.objects.link(tmp)

    if scale:
        tmp.scale = scale
    if apply_rotation:
        tmp.rotation_mode = 'QUATERNION'
        tmp.rotation_quaternion = rotation

    bpy.context.view_layer.objects.active = tmp  # set as the active object in the scene
    tmp.select_set(True)  # select object
        
    # Apply transform (necessary to have correct boundings box)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    filepath = os.path.join(mesh_dir, mesh_name + '.obj')
    export_selected_obj(
        filepath=filepath,
        use_mesh_modifiers=use_mesh_modifiers,
        export_normals=args['export_normals'],
        global_scale=args['global_scale'],
    )

    # scale and rotation are already applied by transform_apply above
    dim, center = get_object_bounding_box(tmp)

    bpy.data.objects.remove(tmp) # remove temporary object
    bpy.data.meshes.remove(tri_mesh)

    # Convert to Roomle Script space
    dim *= args['global_scale']
    center *= args['global_scale']
    center.y *= -1
    bb_origin = center - (dim*0.5)
    dim_str = ( floatFormat(dim.x,1), floatFormat(dim.y,1), floatFormat(dim.z,1) )
    center_str = ( floatFormat(bb_origin.x,1), floatFormat(bb_origin.y,1), floatFormat(bb_origin.z,1) )

    script = 'AddExternalMesh(\'{}:{}\',Vector3f{{{},{},{}}},Vector3f{{{},{},{}}});\n'.format(
        args['catalog_id'],
        mesh_name,
        *dim_str,
        *center_str
        )

    warnings = args['warnings']
    if re.search(r'\.\d{3}$', name):
        warnings.append(f'Mesh id {mesh_name} ends with a Blender number suffix: give the object and its mesh a meaningful name.')

    corto_exe = args['corto_exe']
    if args["use_corto"] and not corto_exe:
        warnings.append(
            'Corto executable not found, external meshes were exported as OBJ. '
            'Set its location in the add-on preferences.'
        )
    elif args["use_corto"]:
        try:
            # Earlier versions passed '-v 12 -n 9 -u 10 -N delta' as one argument, which corto reads as -v 12
            # with defaults for the rest (-n 10 -u 12 -N border). Only -v 12 is passed to keep that output.
            corto_process = subprocess.run(
                [corto_exe, '-v', '12', '-o', crt_filepath, filepath],
                capture_output=True,
                text=True,
            )
            if corto_process.returncode != 0:
                raise Exception((corto_process.stderr or corto_process.stdout).strip())
        except Exception as e:
            warnings.append(f'Corto failed for {os.path.basename(filepath)}, kept the OBJ file: {e}')
        else:
            os.remove(filepath)

    if args['folder_layout'] == 'RLCS' and not os.path.isfile(crt_filepath):
        warnings.append(
            'The Rubens Local Content Server only serves corto files: meshes without corto compression '
            'were exported as OBJ files.'
        )

    return script


def get_used_material_slot(object):
    '''
    the material slot used by all faces, e.g. of the parts split by material in the material export,
    otherwise the first slot
    '''
    indices = {polygon.material_index for polygon in object.data.polygons}
    if len(indices) == 1:
        index = indices.pop()
        if index < len(object.material_slots):
            return object.material_slots[index]
    return object.material_slots[0]


def get_corto_exe(preferences):
    '''
    corto executable from the add-on preferences, otherwise searched on the PATH and in common install folders,
    because Blender started from the Dock or Finder doesn't get the PATH of the shell
    '''
    path = bpy.path.abspath(preferences.corto_exe) if preferences.corto_exe else ''
    if os.path.isfile(path):
        return path
    path = shutil.which('corto')
    if path:
        return path
    for folder in ('~/.local/bin', '/opt/homebrew/bin', '/usr/local/bin'):
        path = os.path.join(os.path.expanduser(folder), 'corto')
        if os.path.isfile(path):
            return path
    return None

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
        x,y,z = map(degrees, (-rot.x,rot.y,-rot.z))
        rotation_precision = 2
        if not isZero(x,rotation_precision):
            command += "RotateMatrixBy(Vector3f{{1,0,0}},Vector3f{{0,0,0}},{});\n".format(floatFormat(x,rotation_precision))
        if not isZero(y,rotation_precision):
            command += "RotateMatrixBy(Vector3f{{0,1,0}},Vector3f{{0,0,0}},{});\n".format(floatFormat(y,rotation_precision))
        if not isZero(z,rotation_precision):
            command += "RotateMatrixBy(Vector3f{{0,0,1}},Vector3f{{0,0,0}},{});\n".format(floatFormat(z,rotation_precision))
    
    # translation
    if parent_scale:
        pos.x = pos.x * parent_scale.x
        pos.y = pos.y * parent_scale.y
        pos.z = pos.z * parent_scale.z

    if apply_rotation and parent_rotation:
        pos = parent_rotation @ pos

    pos = pos @ global_matrix

    if not isZero(pos,precision=1):
        command += "MoveMatrixBy(Vector3f{{{0},{1},{2}}});\n".format(floatFormat(pos.x,1),floatFormat(pos.y,1),floatFormat(pos.z,1))
    
    return command

def create_object_commands(
    preferences,
    object,
    object_list,
    extern_mesh_dir,
    global_matrix,
    parent_scale=None,
    parent_rotation=None,
    apply_transform=False,
    **args
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
    if scale.x==1 and scale.y==1 and scale.z==1:
        scale = None

    apply_rotation = args['apply_rotations']
    rotation = None
    if apply_rotation:
        rotation = object.matrix_world.to_quaternion()
        if rotation.x==0 and rotation.y==0 and rotation.z==0 and rotation.w==1:
            rotation = None

    if object_list==None or (object in object_list):
        # Mesh
        if object.data and isinstance(object.data,bpy.types.Mesh):
            empty = False

            method = args['mesh_export_option']

            extern = (method=='EXTERNAL') or (method=='AUTO' and len(object.data.vertices) > 100)

            if extern:
                mesh = create_extern_mesh_command(
                    preferences,
                     extern_mesh_dir,
                     object,
                     global_matrix,
                     scale=scale,
                     rotation=rotation,
                     **args
                     )
            else:
                mesh = create_mesh_command(object, global_matrix, scale=scale, rotation=rotation, **args)

            # Material
            material = ''
            if object.material_slots:
                material_name = getValidName(get_used_material_slot(object).name)
                # TODO: 5959 create material definition
                material = "SetObjSurface('{}:{}');\n".format( args['catalog_id'], material_name )

    # Children
    childCommands = ''
    if len(object.children)>0:
        for child in object.children:
            if child:
                childCommands += create_object_commands (
                    preferences,
                    child,
                    object_list,
                    extern_mesh_dir,
                    global_matrix, 
                    parent_scale=scale,
                    parent_rotation=rotation,
                    **args
                    )

    hasChildren = bool(childCommands)
    empty = empty and not hasChildren

    if hasChildren:
        command += "BeginObjGroup('{}');\n".format(getValidName(get_export_name(object)))

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

def create_objects_commands(preferences,objects, object_list, extern_mesh_dir, global_matrix, apply_transform=False, **args):
    '''
    Create the Roomle Script command
    iterate over all objects and pass them
    to the create_object_commands
    '''
    command = ''
    if args['debug']:
        command += '/* Roomle script DEBUG */\n'
    else:
        from . import bl_info
        command += '/* Roomle script (Roomle Blender addon version {}) */\n'.format('.'.join( [str(x) for x in bl_info['version']] ))

    object_commands = ''
    for object in objects:
        if object:
            object_commands += create_object_commands(preferences,object, object_list, extern_mesh_dir, global_matrix, **args)

    # nothing exported - the header alone is not a valid export
    if not object_commands.strip():
        return ''
    return (command + object_commands).rstrip()


def get_visible_objects(context: bpy.types.Context):
    view_layer = context.view_layer
    return [obj for obj in view_layer.objects if obj.visible_get(view_layer=view_layer)]


def export_selected_obj(filepath: str, use_mesh_modifiers: bool, export_normals: bool, global_scale: float) -> None:
    if hasattr(bpy.ops.wm, 'obj_export'):
        operator = bpy.ops.wm.obj_export
        properties = inspect.signature(operator).parameters
        kwargs = {
            'filepath': filepath,
            'check_existing': False,
            'global_scale': global_scale,
            'export_selected_objects': True,
            'export_uv': True,
            'export_normals': export_normals,
            'export_materials': False,
            'forward_axis': 'Y',
            'up_axis': 'Z',
        }
        if 'apply_modifiers' in properties:
            kwargs['apply_modifiers'] = use_mesh_modifiers
        if 'export_object_groups' in properties:
            kwargs['export_object_groups'] = False
        if 'export_material_groups' in properties:
            kwargs['export_material_groups'] = False
        operator(**kwargs)
        return

    bpy.ops.export_scene.obj(
        filepath=filepath,
        check_existing=False,
        use_selection=True,
        use_mesh_modifiers=use_mesh_modifiers,
        use_normals=export_normals,
        global_scale=global_scale,
        use_uvs=True,
        use_blen_objects=False,
        use_materials=False,
        axis_forward='Y',
        axis_up='Z',
    )

def write_roomle_script( operator, preferences, context, filepath, global_matrix, **args ):
    """
    Write a roomle script file from faces,

    filepath
       output filepath

    faces
       iterable of tuple of 3 vertex, vertex is tuple of 3 coordinates as float
    """
    # exceptions are not caught here, the operator reports them to the user
    scene = bpy.context.scene

    root_objects = []
    for obj in scene.objects:
        if not obj.parent:
            root_objects.append(obj)

    object_list = bpy.context.selected_objects if args['use_selection'] else get_visible_objects(bpy.context)

    extern_mesh_dir = os.path.splitext(filepath)[0]

    script = create_objects_commands(preferences,root_objects,object_list,extern_mesh_dir,global_matrix,**args)
    if not bool(script):
        raise Exception('Empty export! Make sure you have meshes selected.')
    else:
        with open(filepath, 'w') as data:
            data.write(script)
