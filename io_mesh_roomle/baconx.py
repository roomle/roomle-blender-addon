import bpy
import re,os,subprocess

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

    mesh.calc_normals()

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

    mesh.calc_normals()

    uvsPresent = mesh.tessface_uv_textures.active!=None
    if uvsPresent:
        uvsSrc = mesh.tessface_uv_textures.active.data
    
    if triangulate:
        # From a list of faces, return the face triangulated if needed.
        def iter_face_index():
            for i, face in enumerate(mesh.tessfaces):
                vertices = face.vertices[:]

                if len(vertices) == 4:
                    yield (vertices[0], vertices[2], vertices[1])
                    yield (vertices[2], vertices[0], vertices[3])
                else:
                    yield (vertices[0], vertices[2], vertices[1])
        if uvsPresent:
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
                        (uvFace.uv3.x,uvFace.uv3.y),\
                        (uvFace.uv2.x,uvFace.uv2.y)
                        #for uv in uvFace.uv:
                        #   yield (uv[0],uv[1])
    else:
        def iter_face_index():
            for i, face in enumerate(mesh.tessfaces):
                yield face.vertices[:]
        if uvsPresent:
            def iter_uvs():
                for uvFace in uvsSrc:
                    for uv in uvFace.uv:
                        yield (uv[0],uv[1])

    vertices = []
    normals = []

    for v in mesh.vertices:
        vertices.append(v.co)
        # for some weird reason I have to invert the normal here.
        # dunno why
        normals.append(v.normal * -1)

    indices = []

    for indexes in iter_face_index():
        indices += indexes

    tmpDict = {}

    split_uvs = False

    if uvsPresent:
        uvs = []
        tmpUvs = {}
        for uv in iter_uvs():
            uvs += uv

        for i, vuv in enumerate(zip(indices,uvs)):
            
            oldIndex = vuv[0]
            uv = vuv[1]

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

        uvs = list(tmpUvs.values())
    else:
        uvs = None

    # print('uv len {}'.format(len(uvs)))
    # print('indices len {}'.format(len(indices)))
    # print('vertices len {}'.format(len(vertices)))

    '''
    TODO: if the temporary mesh is removed here, things (position values) go nuts. fixit!
    '''
    # bpy.data.meshes.remove(mesh)
    return vertices, indices, uvs, normals, split_uvs
        
def create_mesh_command( object, global_matrix, use_mesh_modifier = True, export_normals = True ):
    
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

def create_extern_mesh_command( preferences, extern_mesh_dir, object, global_matrix, catalog_id, use_mesh_modifier = True, export_normals = False ):

    mesh = object.data
    name = mesh.name

    if not os.path.isdir(extern_mesh_dir):
        os.makedirs(extern_mesh_dir)

    filepath = os.path.join( extern_mesh_dir, '{}.{}'.format(name,'ply') )
    
    scene = bpy.context.scene
    
    tmp = bpy.data.objects.new('tmp_'+name, mesh) # create temporary object with same mesh data but without transformation
    scene.objects.link(tmp)  # put the object into the scene (link)

    scene.objects.active = tmp  # set as the active object in the scene
    tmp.select = True  # select object
        
    bpy.ops.export_mesh.ply(
        filepath=filepath,
        check_existing=False,
        axis_forward='Y',
        axis_up='Z',
        filter_glob="*.ply",
        use_mesh_modifiers=False,
        use_normals=export_normals,
        use_uv_coords=False,
        use_colors=False,
        global_scale=1000
        )

    bpy.data.objects.remove(tmp,True) # remove temporary object

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
    
    dim = object.dimensions * 1000
    bounds = ( floatFormat(dim.x,1), floatFormat(dim.z,1), floatFormat(dim.y,1) )

    script_name = os.path.basename(extern_mesh_dir)
    script = 'AddExternalMesh(\'{}:{}_{}\',Vector3f{{{},{},{}}});'.format(catalog_id,script_name,name,*bounds)
    
    return script

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
        command += "RotateMatrixBy(Vector3f{{1,0,0}},Vector3f{{0,0,0}},{});".format(floatFormat(x,2))
    if y!=0:
        command += "RotateMatrixBy(Vector3f{{0,1,0}},Vector3f{{0,0,0}},{});".format(floatFormat(y,2))
    if z!=0:
        command += "RotateMatrixBy(Vector3f{{0,0,1}},Vector3f{{0,0,0}},{});".format(floatFormat(z,2))
    
    # translation
    if not isZero(pos):
        command += "MoveMatrixBy(Vector3f{{{0},{1},{2}}});".format(floatFormat(pos.x,1),floatFormat(pos.y,1),floatFormat(pos.z,1))
    
    return command

def create_object_commands(preferences,object, object_list, extern_mesh_dir, global_matrix, catalog_id, export_normals=False, apply_transform=False):
    command = ''
    
    empty = True

    mesh = ''
    material = ''

    if object_list==None or (object in object_list):
        # Mesh
        if object.data and type(object.data)==bpy.types.Mesh:
            empty = False

            method = object.data.roomle_export_method

            extern = (method=='EXTERNAL') or (method=='AUTO' and len(object.data.vertices) > 100)

            if extern:
                mesh = create_extern_mesh_command( preferences, extern_mesh_dir, object, global_matrix, catalog_id, export_normals=export_normals )
            else:
                mesh = create_mesh_command(object, global_matrix, export_normals=export_normals)

            # Material
            material_name = 'default'
            if object.material_slots:
                material_name = getValidName(object.material_slots[0].name)
            material = "SetObjSurface('{}:{}');".format(catalog_id,material_name)

    # Children
    childCommands = ''
    if len(object.children)>0:
        for child in object.children:
            if child:
                childCommands += create_object_commands(preferences,child, object_list, extern_mesh_dir, global_matrix, catalog_id, export_normals)

    hasChildren = bool(childCommands)
    empty = empty and not hasChildren

    if hasChildren:
        command += "BeginObjGroup('{}');".format(getValidName(object.name))

    command += mesh
    command += material

    if hasChildren:
        command += childCommands
        command += "EndObjGroup();"
        
    # Transform
    if not apply_transform and not empty:
        command += create_transform_commands(object, global_matrix)

    return command

def create_objects_commands(preferences,objects, object_list, extern_mesh_dir, global_matrix, catalog_id, export_normals=False, apply_transform=False):
    command = ''
    for object in objects:
        if object:
            command += create_object_commands(preferences,object, object_list, extern_mesh_dir, global_matrix, catalog_id, export_normals)
    return command

def write_roomle_script( operator, preferences, context, filepath, global_matrix, catalog_id='catalog_id', export_normals=False, use_selection=False ):
    """
    Write a roomle script file from faces,

    filepath
       output filepath

    faces
       iterable of tuple of 3 vertex, vertex is tuple of 3 coordinates as float
    """

    scene = bpy.context.scene

    root_objects = []
    for obj in scene.objects:
        if not obj.parent:
            root_objects.append(obj)
    
    object_list = bpy.context.selected_objects if use_selection else None

    extern_mesh_dir = os.path.splitext(filepath)[0]

    script = create_objects_commands(preferences,root_objects,object_list,extern_mesh_dir,global_matrix,catalog_id,export_normals)
    if not bool(script):
        raise Exception('Empty export! Make sure you have meshes selected.')
    else:
        with open(filepath, 'w') as data:
            data.write(script)