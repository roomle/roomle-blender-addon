import bpy
import bmesh
import re,os,subprocess

from decimal import Decimal
from math import degrees,floor,log10

from mathutils import Vector

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
    result = '{:f}'.format(d.quantize(q).normalize())
    return '0' if result == '-0' else result

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
        
def create_mesh_command( object, global_matrix, use_mesh_modifiers = True, **args ):
    
    command = '//Mesh:{}\n'.format(object.data.name)
    command += 'AddMesh('
    export_normals = args['export_normals']

    vertices, indices, uvs, normals, split_uvs = indices_from_mesh(object,global_matrix,use_mesh_modifiers)
    
    export_normals |= split_uvs

    command += 'Vector3f['
    command += ','.join( '{{{0},{1},{2}}}'.format( floatFormat(v.x,1), floatFormat(v.y,1), floatFormat(v.z,1) ) for v in vertices)
    command += '],'
    
    command += '['
    command += ','.join(map(str,indices))
    command += ']'
    
    if uvs:
        maxvalue = 1
        for p in uvs:
            maxvalue = max(maxvalue, *[abs(x) for x in p] )

        uv_prec = max( 0, args['uv_float_precision'] - floor(log10(abs(maxvalue))))

        command+=',Vector2f['
        command += ','.join( '{{{0},{1}}}'.format( floatFormat(p[0],uv_prec), floatFormat(p[1],uv_prec) ) for p in uvs)
        command+=']'

    if export_normals:
        norm_prec = args['normal_float_precision']

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

def create_extern_mesh_command( preferences, extern_mesh_dir, object, global_matrix, use_mesh_modifiers = True, **args ):

    mesh = object.data
    name = mesh.name

    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(mesh)

    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=0, ngon_method=0)

    tri_mesh = bpy.data.meshes.new(name)

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(tri_mesh)
    bm.free()

    if not os.path.isdir(extern_mesh_dir):
        os.makedirs(extern_mesh_dir)

    filepath = os.path.join( extern_mesh_dir, '{}.{}'.format(name,'ply') )
    
    scene = bpy.context.scene
    
    tmp = bpy.data.objects.new('tmp_'+name, tri_mesh) # create temporary object with same mesh data but without transformation
    scene.objects.link(tmp)  # put the object into the scene (link)

    scene.objects.active = tmp  # set as the active object in the scene
    tmp.select = True  # select object
        
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

    bpy.data.objects.remove(tmp,True) # remove temporary object
    bpy.data.meshes.remove(tri_mesh,True)

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
    
    dim, center = get_object_bounding_box(object)
    # Convert to Roomle Script space
    dim *= 1000
    center *= 1000
    center.y *= -1
    dim_str = ( floatFormat(dim.x,1), floatFormat(dim.y,1), floatFormat(dim.z,1) )
    center_str = ( floatFormat(center.x,1), floatFormat(center.y,1), floatFormat(center.z,1) )

    script_name = os.path.basename(extern_mesh_dir)
    script = 'AddExternalMesh(\'{}:{}_{}\',Vector3f{{{},{},{}}},Vector3f{{{},{},{}}});\n'.format(
        args['catalog_id'],
        script_name,
        name,
        *dim_str,
        *center_str
        )
    
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
        command += "RotateMatrixBy(Vector3f{{1,0,0}},Vector3f{{0,0,0}},{});\n".format(floatFormat(x,2))
    if y!=0:
        command += "RotateMatrixBy(Vector3f{{0,1,0}},Vector3f{{0,0,0}},{});\n".format(floatFormat(y,2))
    if z!=0:
        command += "RotateMatrixBy(Vector3f{{0,0,1}},Vector3f{{0,0,0}},{});\n".format(floatFormat(z,2))
    
    # translation
    if not isZero(pos):
        command += "MoveMatrixBy(Vector3f{{{0},{1},{2}}});\n".format(floatFormat(pos.x,1),floatFormat(pos.y,1),floatFormat(pos.z,1))
    
    return command

def create_object_commands(
    preferences,
    object,
    object_list,
    extern_mesh_dir,
    global_matrix,
    apply_transform=False,
    **args
    ):

    command = ''
    
    empty = True

    mesh = ''
    material = ''

    if object_list==None or (object in object_list):
        # Mesh
        if object.data and type(object.data)==bpy.types.Mesh:
            empty = False

            method = args['mesh_export_option']

            extern = (method=='EXTERNAL') or (method=='AUTO' and len(object.data.vertices) > 100)

            if extern:
                mesh = create_extern_mesh_command( preferences, extern_mesh_dir, object, global_matrix, **args )
            else:
                mesh = create_mesh_command(object, global_matrix, **args)

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
                childCommands += create_object_commands(preferences,child, object_list, extern_mesh_dir, global_matrix, **args)

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
        command += create_transform_commands(object, global_matrix)

    return command

def create_objects_commands(preferences,objects, object_list, extern_mesh_dir, global_matrix, apply_transform=False, **args):
    command = ''
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