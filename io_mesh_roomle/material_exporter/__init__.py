from pathlib import Path
import bpy

from io_mesh_roomle.material_exporter._exporter import RoomleMaterialExporter


class SceneHandler():
    def __init__(self, scene: bpy.types.Scene) -> None:
        self.scene = scene
        # store existing collections so we can delete duplicates after export
        self.existing_collections = set(bpy.data.collections)

    def copy_scene(self):
        bpy.ops.scene.new(type='FULL_COPY')
        return self

    def remove_export_scene(self):
        scene = self.scene
        """Delete a scene and all its objects."""
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
        for coll in set(bpy.data.collections) - self.existing_collections:
            bpy.data.collections.remove(coll)

        # Remove scene.
        bpy.data.scenes.remove(scene, do_unlink=True)

        # open the scene were we started from
        bpy.context.window.scene = self.scene


def split_object_by_materials(obj) -> set:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    # obj.name = get_valid_name(obj.name)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.editmode_toggle()

    return set(bpy.context.selected_objects)


def export_materials(**keywords):

    # get the objects to export

    if keywords["use_selection"]:
        obj_list = bpy.context.selected_objects
    else:
        obj_list = bpy.context.scene.objects

    mesh_objs_to_export = set(filter(lambda obj: obj.type == 'MESH', obj_list))

    for obj in mesh_objs_to_export:
        material_parts = split_object_by_materials(obj)
        # add new mesh fragments to export objects
        mesh_objs_to_export.update(material_parts)

    RoomleMaterialExporter(mesh_objs_to_export,
                           out_path=Path(keywords['filepath']).parent)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs_to_export: #| selection_to_restore:
        obj.select_set(True)