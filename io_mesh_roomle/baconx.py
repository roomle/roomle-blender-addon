import bpy
import re

from math import degrees

from bpy_extras.io_utils import (
        axis_conversion,
        )

def getValidName(name):
    return re.sub('[^0-9a-zA-Z:_]+', '', name)

def isZero(self):
    return not any(f!=0 for f in self)

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

def indices_from_mesh(ob, global_matrix, use_mesh_modifiers=False, triangulate=True):

    # get the editmode data
    ob.update_from_editmode()

    # get the modifiers
    try:
        mesh = ob.to_mesh(bpy.context.scene, use_mesh_modifiers, "PREVIEW")
    except RuntimeError:
        raise StopIteration

    mesh.transform(global_matrix * ob.matrix_world)

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
    indices = []
    
    for indexes in iter_face_index():
        indices += indexes
        
    bpy.data.meshes.remove(mesh)
    return vertices, indices
        
def create_mesh_command( object, global_matrix, triangle_strip = True, use_mesh_modifier = True ):
    
    faces = faces_from_mesh(object, global_matrix, True)
    
    mesh = object.data
    
    command = "Mesh({},".format(getValidName(object.name));
    if triangle_strip:
        command += 'Vector3f['
        command += ','.join(
            '{{{},{},{}}}'.format(
                v.x,v.y,v.z
                ) for v in vertices_from_mesh(object,global_matrix,use_mesh_modifier))
        command += ']'
    else:
        
        vertices, indices = indices_from_mesh(object,global_matrix,use_mesh_modifier)
        
        command += '['
        command += ','.join( '{{{},{},{}}}'.format( v.co.x, v.co.y, v.co.z ) for v in vertices)
        command += '],'
        
        command += '['
        command += ','.join(map(str,indices))
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
        command += "RotateMatrixBy(Vector3f{{1,0,0}},Vector3f{{0,0,0}},{});".format(x)
    if y!=0:
        command += "RotateMatrixBy(Vector3f{{0,1,0}},Vector3f{{0,0,0}},{});".format(y)
    if z!=0:
        command += "RotateMatrixBy(Vector3f{{0,0,1}},Vector3f{{0,0,0}},{});".format(z)
    
    # translation
    if not isZero(pos):
        command += "MoveMatrixBy(Vector3f{{{},{},{}}});".format(pos.x,pos.y,pos.z)
    
    #command += "ScaleMatrixBy({},{},{});".format(scale.x,scale.y,scale.z)
    return command

def create_object_commands(object, global_matrix, apply_transform=False):
    command = ''
    
    # Mesh
    mesh = create_mesh_command(object, global_matrix)
    
    # Material
    material = "SetObjSurface('default');"
    if bpy.context.active_object.material_slots:
        material = "SetObjSurface('{}');".format(getValidName(bpy.context.active_object.material_slots[0].name))
    
    # Children
    if len(object.children)>0:
        command += "BeginObjGroup('{}');".format(getValidName(object.name))
        command += mesh
        command += material
        for child in object.children:
            command += create_object_commands(child, global_matrix)
        command += "EndObjGroup();"
    else:
        command += mesh
        command += material
        
    # Transform
    if not apply_transform:
        command += create_transform_commands(object, global_matrix)

    return command

def write_roomle_script(filepath, object, global_matrix):
    """
    Write a roomle script file from faces,

    filepath
       output filepath

    faces
       iterable of tuple of 3 vertex, vertex is tuple of 3 coordinates as float
    """
    with open(filepath, 'w') as data:
        data.write(create_object_commands( object, global_matrix ))

# from mathutils import Matrix, Vector

# global_scale = 1000
# global_matrix = axis_conversion(to_forward='-Y',to_up='Z',).to_4x4() * Matrix.Scale(global_scale, 4) * Matrix.Scale(-1,4,Vector((1,0,0)))

# command = create_object_commands(bpy.context.active_object, global_matrix)
# command = '{"id":"catalogExtId:component1","geometry":"'+command+'"}'

# if 'Commands' in bpy.data.texts:
#     text = bpy.data.texts['Commands']
# else:
#     bpy.ops.text.new()
#     text = bpy.data.texts[-1]
#     text.name = 'Commands'

# text.from_string(command)