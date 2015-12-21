import bpy
import re

from decimal import Decimal
from math import degrees

from bpy_extras.io_utils import (
        axis_conversion,
        )

def getValidName(name):
    return re.sub('[^0-9a-zA-Z:_]+', '', name)

def isZero(self):
    return not any(f!=0 for f in self)

def floatFormat( value, precision=0 ):
    """
    Converts a float to a string. Rounds to a certain precision and removed trailing zeros.
    """
    q = Decimal(10) ** -precision      # 2 precision --> '0.01'
    d = Decimal(value)
    return '{:f}'.format(d.quantize(q).normalize())

def is_child(parent, child):
    for c in parent.children:
        if c==child:
            return True
        if is_child(c,child):
            return True
    return False

def remove_nested_objects(objects):
    for o in objects:
        for c in objects:
            if o==c:
                continue
            print('check' + c.name + ' in '+o.name)
            if is_child(o,c):
                print('remove' + str(c))
                objects.remove(c)
    return objects

def faces_from_mesh(ob, global_matrix, use_mesh_modifiers=False, triangulate=True, apply_transform=False):
    """
    From an object, return a generator over a list of faces.

    Each faces is a list of his vertexes. Each vertex is a tuple of
    his coordinate.

    use_mesh_modifiers
        Apply the preview modifier to the returned liste

    triangulate
        Split the quad into two triangles
    """

    # get the editmode data
    ob.update_from_editmode()

    # get the modifiers
    try:
        mesh = ob.to_mesh(bpy.context.scene, use_mesh_modifiers, "PREVIEW")
    except RuntimeError:
        raise StopIteration

    if apply_transform:
        mesh.transform(global_matrix * ob.matrix_world)
    else:
        mesh.transform(global_matrix)

    if triangulate:
        # From a list of faces, return the face triangulated if needed.
        def iter_face_index():
            for face in mesh.tessfaces:
                vertices = face.vertices[:]
                if len(vertices) == 4:
                    yield vertices[0], vertices[2], vertices[1]
                    yield vertices[2], vertices[0], vertices[3]
                else:
                    yield vertices[0], vertices[2], vertices[1]
    else:
        def iter_face_index():
            for face in mesh.tessfaces:
                yield face.vertices[:]

    vertices = mesh.vertices

    for indexes in iter_face_index():
        yield [vertices[index].co.copy() for index in indexes]

    bpy.data.meshes.remove(mesh)

def vertices_from_mesh(ob, global_matrix, use_mesh_modifiers=False, triangulate=True):
    for f in faces_from_mesh(ob, global_matrix, use_mesh_modifiers=False, triangulate=True):
        for v in f:
            yield v

def indices_from_mesh(ob, global_matrix, use_mesh_modifiers=False, triangulate=True, apply_transform=False):

    # get the editmode data
    ob.update_from_editmode()

    # get the modifiers
    try:
        mesh = ob.to_mesh(bpy.context.scene, use_mesh_modifiers, "PREVIEW")
    except RuntimeError:
        raise StopIteration

    if apply_transform:
        mesh.transform(global_matrix * ob.matrix_world)
    else:
        mesh.transform(global_matrix)

    uvsSrc = mesh.tessface_uv_textures.active.data
    
    if triangulate:
        # From a list of faces, return the face triangulated if needed.
        def iter_face_index():
            for i, face in enumerate(mesh.tessfaces):
                vertices = face.vertices[:]
                uvs = mesh.tessface_uv_textures.active.data[i].uv

                if len(vertices) == 4:
                    yield (vertices[0], vertices[2], vertices[1])
                    yield (vertices[2], vertices[0], vertices[3])
                else:
                    yield (vertices[0], vertices[2], vertices[1])

        def iter_uvs():
            for uvFace in uvsSrc:
                if(len(uvFace.uv)==4):
                    yield (uvFace.uv1.x,uvFace.uv1.y),\
                    (uvFace.uv3.x,uvFace.uv3.y),\
                    (uvFace.uv2.x,uvFace.uv2.y),\
                    (uvFace.uv3.x,uvFace.uv3.y),\
                    (uvFace.uv1.x,uvFace.uv1.y),\
                    (uvFace.uv4.x,uvFace.uv4.y)
                else:
                    yield (uvFace.uv1.x,uvFace.uv1.y),\
                    (uvFace.uv2.x,uvFace.uv2.y),\
                    (uvFace.uv3.x,uvFace.uv3.y)
                    #for uv in uvFace.uv:
                    #   yield (uv[0],uv[1])
    else:
        def iter_face_index():
            for i, face in enumerate(mesh.tessfaces):
                yield face.vertices[:]

        def iter_uvs():
            for uvFace in uvsSrc:
                for uv in uvFace.uv:
                    yield (uv[0],uv[1])


    vertices = []
    normals = []

    for v in mesh.vertices:
        vertices.append(v.co)
        normals.append(v.normal)

    indices = []
    uvs = []

    for indexes in iter_face_index():
        indices += indexes

    for uv in iter_uvs():
        uvs += uv

    tmpIndices = []
    tmpUvs = {}
    tmpDict = {}

    split_uvs = False

    for i, vuv in enumerate(zip(indices,uvs)):
        
        oldIndex = vuv[0]
        uv = vuv[1]

        print(i,oldIndex,uv)

        if oldIndex in tmpDict:
            if uv in tmpDict[oldIndex]:
                split_uvs = True
                newIndex = tmpDict[oldIndex][uv]
            else:
                # duplicate vertex
                newIndex = len(vertices)
                vertices.append( vertices[oldIndex] )
                normals.append( normals[oldIndex] )
                tmpDict[oldIndex][uv] = newIndex
            indices[i] = newIndex
            tmpUvs[newIndex] = uv
        else:
            tmpDict[oldIndex] = { uv : oldIndex }
            tmpUvs[oldIndex] = uv

    for k,v in tmpUvs.items():
        print(k,v)

    uvs = list(tmpUvs.values())

    # print('uv len {}'.format(len(uvs)))
    # print('indices len {}'.format(len(indices)))
    # print('vertices len {}'.format(len(vertices)))

    '''
    TODO: if the temporary mesh is removed here, things (position values) go nuts. fixit!
    '''
    # bpy.data.meshes.remove(mesh)
    return vertices, indices, uvs, normals, split_uvs
        
def create_mesh_command( object, global_matrix, use_mesh_modifier = True, export_normals = True ):
    
    faces = faces_from_mesh(object, global_matrix, True)
    
    mesh = object.data
    
    command = "AddMesh("
        
    vertices, indices, uvs, normals, split_uvs = indices_from_mesh(object,global_matrix,use_mesh_modifier)
    
    export_normals |= split_uvs

    command += 'Vector3f['
    command += ','.join( '{{{0},{1},{2}}}'.format( floatFormat(v.x,1), floatFormat(v.y,1), floatFormat(v.z,1) ) for v in vertices)
    command += '],'
    
    command += '['
    command += ','.join(map(str,indices))
    command += ']'
    
    if uvs:
        command+=',Vector2f['
        command += ','.join( '{{{0},{1}}}'.format( floatFormat(p[0],6), floatFormat(p[1],6) ) for p in uvs)
        command+=']'

    if export_normals:
        command += ',Vector3f['
        command += ','.join( '{{{0},{1},{2}}}'.format( floatFormat(n.x,8), floatFormat(n.y,8), floatFormat(n.z,8) ) for n in normals)
        command += ']'
        
    command+=');'
    return command

def create_transform_commands( object, global_matrix ):
    command = ''
    pos = object.matrix_local.translation*global_matrix
    rot = object.matrix_local.to_euler()
    scale = object.scale
    
    if scale.x!=1 or scale.y!=1 or scale.z!=1:
        raise Exception("Object {} has scale on it. Fix it first.".format(object.name))
    
    # rotation
    x,y,z = map(degrees, (-rot.x,rot.y,-rot.z))
    if x!=0:
        command += "RotateMatrixBy(Vector3f{{1,0,0}},Vector3f{{0,0,0}},{});".format(floatFormat(x,8))
    if y!=0:
        command += "RotateMatrixBy(Vector3f{{0,1,0}},Vector3f{{0,0,0}},{});".format(floatFormat(y,8))
    if z!=0:
        command += "RotateMatrixBy(Vector3f{{0,0,1}},Vector3f{{0,0,0}},{});".format(floatFormat(z,8))
    
    # translation
    if not isZero(pos):
        command += "MoveMatrixBy(Vector3f{{{0},{1},{2}}});".format(floatFormat(pos.x,1),floatFormat(pos.y,1),floatFormat(pos.z,1))
    
    return command

def create_object_commands(object, global_matrix, export_normals=False, apply_transform=False):
    command = ''
    
    # Mesh
    mesh = ''
    if object.data:
        mesh = create_mesh_command(object, global_matrix, export_normals=export_normals)
    
    # Material
    material = "SetObjSurface('default');"
    if object.material_slots:
        material = "SetObjSurface('{}');".format(getValidName(object.material_slots[0].name))
    
    # Children
    if len(object.children)>0:
        command += "BeginObjGroup('{}');".format(getValidName(object.name))
        command += mesh
        command += material
        for child in object.children:
            command += create_object_commands(child, global_matrix, export_normals)
        command += "EndObjGroup();"
    else:
        command += mesh
        command += material
        
    # Transform
    if not apply_transform:
        command += create_transform_commands(object, global_matrix)

    return command

def create_objects_commands(objects, global_matrix, export_normals=False, apply_transform=False):
    command = ''
    for object in objects:
        command += create_object_commands(object, global_matrix, export_normals)
    return command

def write_roomle_script(filepath, objects, global_matrix, export_normals=False):
    """
    Write a roomle script file from faces,

    filepath
       output filepath

    faces
       iterable of tuple of 3 vertex, vertex is tuple of 3 coordinates as float
    """

    filterted_objects = remove_nested_objects(objects)

    with open(filepath, 'w') as data:
        data.write(create_objects_commands(filterted_objects,global_matrix,export_normals))

from mathutils import Matrix, Vector

global_scale = 1000
global_matrix = axis_conversion(to_forward='-Y',to_up='Z',).to_4x4() * Matrix.Scale(global_scale, 4) * Matrix.Scale(-1,4,Vector((1,0,0)))

objects = remove_nested_objects(bpy.context.selected_objects)
command = create_objects_commands(objects,global_matrix)
command = '{"id":"catalogExtId:component1","geometry":"'+command+'"}'

if 'Commands' in bpy.data.texts:
    text = bpy.data.texts['Commands']
else:
    bpy.ops.text.new()
    text = bpy.data.texts[-1]
    text.name = 'Commands'

text.from_string(command)