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
import subprocess

from dataclasses import dataclass
from decimal import Decimal
from math import degrees,floor,log10
from copy import deepcopy

from mathutils import Vector

from bpy_extras.io_utils import (
        axis_conversion,
        )

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

    mesh.calc_normals()
    mesh.calc_loop_triangles()
    #mesh.calc_normals_split()
    
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

    command = '//Object:{} Mesh:{}\n'.format(object.name,object.data.name)
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

    apply_rotation = args['apply_rotations'] and rotation
    name = object.name if (scale or apply_rotation) else object.data.name

    mesh = object.to_mesh(
        depsgraph=bpy.context.evaluated_depsgraph_get(),
    )

    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(mesh)

    bmesh.ops.triangulate(bm,faces=bm.faces[:])

    tri_mesh = bpy.data.meshes.new(name)

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(tri_mesh)
    bm.free()

    if not os.path.isdir(extern_mesh_dir):
        os.makedirs(extern_mesh_dir)

    script_name = os.path.basename(extern_mesh_dir)
    filepath = os.path.join( extern_mesh_dir, '{}_{}.{}'.format(script_name,name,'ply') )
    
    scene = bpy.context.scene
    
    bpy.ops.object.select_all(action='DESELECT')

    tmp = bpy.data.objects.new('tmp_'+name, tri_mesh) # create temporary object with same mesh data but without transformation
    
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

    bpy.ops.export_mesh.ply(
        filepath=filepath,
        check_existing=False,
        axis_forward='Y',
        axis_up='Z',
        filter_glob="*.ply",
        use_mesh_modifiers=use_mesh_modifiers,
        use_normals=args['export_normals'],
        use_uv_coords=True,
        use_colors=False,
        global_scale=1000
        )

    dim, center = get_object_bounding_box(tmp)

    bpy.data.objects.remove(tmp) # remove temporary object
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
    dim_str = ( floatFormat(dim.x,1), floatFormat(dim.y,1), floatFormat(dim.z,1) )
    center_str = ( floatFormat(bb_origin.x,1), floatFormat(bb_origin.y,1), floatFormat(bb_origin.z,1) )

    script = 'AddExternalMesh(\'{}:{}_{}\',Vector3f{{{},{},{}}},Vector3f{{{},{},{}}});\n'.format(
        args['catalog_id'],
        script_name,
        name,
        *dim_str,
        *center_str
        )

    if preferences.corto_exe and os.path.isfile(preferences.corto_exe):
        try:
            corto_process = subprocess.Popen( [preferences.corto_exe,filepath] )
            if corto_process.wait()!=0:
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
                mesh = create_extern_mesh_command( preferences, extern_mesh_dir, object, global_matrix, scale=scale, rotation=rotation, **args )
            else:
                mesh = create_mesh_command(object, global_matrix, scale=scale, rotation=rotation, **args)

            # Material
            material_name = 'default'
            if object.material_slots:
                material_name = getValidName(object.material_slots[0].name)
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
        command += "BeginObjGroup('{}');\n".format(getValidName(object.name))

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
    command = ''
    if args['debug']:
        command += '// Roomle script DEBUG\n'
    else:
        from . import bl_info
        command += '// Roomle script (Roomle Blender addon version {})\n'.format('.'.join( [str(x) for x in bl_info['version']] ))

    for object in objects:
        if object:
            command += create_object_commands(preferences,object, object_list, extern_mesh_dir, global_matrix, **args)
    return command.rstrip()

def write_roomle_script( operator, preferences, context, filepath, global_matrix, **args ):
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
        
        object_list = bpy.context.selected_objects if args['use_selection'] else bpy.context.visible_objects

        extern_mesh_dir = os.path.splitext(filepath)[0]

        script = create_objects_commands(preferences,root_objects,object_list,extern_mesh_dir,global_matrix,**args)
        if not bool(script):
            raise Exception('Empty export! Make sure you have meshes selected.')
        else:
            with open(filepath, 'w') as data:
                data.write(script)
    except Exception as e:
        import traceback
        print('Exception',e)
        x = traceback.format_exc()
        print(x)