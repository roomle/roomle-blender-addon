import bpy
from pathlib import Path
from ._exporter import RoomleMaterialExporter

STARTING_SCENE = None
EXISTING_COLLECTIONS = set()

def remove_export_scene(scene=None):
    global STARTING_SCENE
    global EXISTING_COLLECTIONS
    """Delete a scene and all its objects."""
    #
    # Sort out the scene object.
    if scene is None:
        # Not specified: it's the current scene.
        scene = bpy.context.scene
    else:
        if isinstance(scene, str):
            scene = bpy.data.scenes[scene]

    # collect all data blocks that need
    # to be removed in sets, where the key
    # matches the object type
    data_blocks = {
        'LIGHT': {
            'data': set(),
            'fn_remove': bpy.data.lights.remove,
        },
        'CAMERA': {
            'data': set(),
            'fn_remove': bpy.data.cameras.remove,
        },
        'MESH': {
            'data': set(),
            'fn_remove': bpy.data.meshes.remove,
        },
    }

    # collect data blocks to remove
    for object_ in scene.objects:
        obj_type = object_.type
        if obj_type not in data_blocks:
            print(f't not found')
        data_blocks[obj_type]['data'].add(object_.data)

    # remove the actual data blocks
    for data_block_entry in data_blocks.values():
        for block in data_block_entry['data']:
            data_block_entry['fn_remove'](block, do_unlink=True)

    # Remove World
    # Scene `full copy` also duplicates the world -> we need to delete it
    world = bpy.context.scene.world
    if world is not None:
        bpy.data.worlds.remove(world)

    # remove collections created by scene duplication
    for coll in set(bpy.data.collections) - EXISTING_COLLECTIONS:
        bpy.data.collections.remove(coll)
        
    # Remove scene.
    bpy.data.scenes.remove(scene, do_unlink=True)

    # open the scene were we started from
    bpy.context.window.scene = bpy.data.scenes[STARTING_SCENE]


def export_materials(**keywords):
    global STARTING_SCENE
    STARTING_SCENE = bpy.context.scene.name

    # store existing collections so we can delete duplicates after export
    global EXISTING_COLLECTIONS
    EXISTING_COLLECTIONS = set(bpy.data.collections)

    # copy the full scene to work on
    bpy.ops.scene.new(type='FULL_COPY')

    # we need to restore the current selection after the material export
    # some objects may get separated by material – this objects will be added later
    selection_to_restore = set(bpy.context.selected_objects)

    # get the objects to export
    obj_list = bpy.context.selected_objects if keywords[
        "use_selection"] else bpy.context.scene.objects
    mesh_objs_to_export = set(filter(lambda obj: obj.type == 'MESH', obj_list))

    for obj in set(mesh_objs_to_export):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        # obj.name = get_valid_name(obj.name)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.editmode_toggle()

        for exp in bpy.context.selected_objects:
            mesh_objs_to_export.add(exp)

    RoomleMaterialExporter(mesh_objs_to_export,
                           out_path=Path(keywords['filepath']).parent)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs_to_export | selection_to_restore:
        obj.select_set(True)
