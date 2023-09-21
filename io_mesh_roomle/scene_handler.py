import bpy
import logging

log = logging.getLogger(__file__)

class SceneHandler():
    def __init__(self, scene: bpy.types.Scene) -> None:
        self.original_scene = scene
        # store existing collections so we can delete duplicates after export
        self.existing_collections = set(bpy.data.collections)

    def copy_scene(self):
        bpy.ops.scene.new(type='FULL_COPY')
        return self

    def remove_export_scene(self, scene = None):
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
            'EMPTY': {
                'data': set(),
                'fn_remove': bpy.data.objects.remove,
            },
        }

        # collect data blocks to remove
        for object_ in scene.objects:
            obj_type = object_.type
            if obj_type not in data_blocks:
                print(f't not found')
            try:
                #TODO: check why object_.data cane end up as exception string
                data_blocks[obj_type]['data'].add(object_.data)
            except Exception as e:
                log.error('❌ error when removing object from export scene')
                log.debug(e)

        # remove the actual data blocks
        for data_block_entry in data_blocks.values():
            for block in data_block_entry['data']:
                try:
                    data_block_entry['fn_remove'](block, do_unlink=True)
                except Exception as e:
                    log.error('❌ error when removing object from export scene')
                    log.debug(e)

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
        bpy.context.window.scene = self.original_scene