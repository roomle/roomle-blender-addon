import bpy
import logging

log = logging.getLogger(__file__)

# custom property with the original name of an object or mesh, copied along with the scene
EXPORT_NAME_PROPERTY = 'roomle_export_name'


def get_export_name(id_data) -> str:
    '''name of an object or mesh in the scene of the user, also for its copy in the export scene'''
    return id_data.get(EXPORT_NAME_PROPERTY, id_data.name)


class SceneHandler():
    def __init__(self, scene: bpy.types.Scene) -> None:
        self.original_scene = scene
        self.export_scene = None
        self.named_ids = []
        # store existing collections so we can delete duplicates after export
        self.existing_collections = set(bpy.data.collections)

    def copy_scene(self):
        # copies get suffixes like .001, the original names keep the mesh ids independent of the material export
        for obj in self.original_scene.objects:
            for id_data in (obj, obj.data if isinstance(obj.data, bpy.types.Mesh) else None):
                if id_data is not None:
                    id_data[EXPORT_NAME_PROPERTY] = id_data.name
                    self.named_ids.append(id_data)

        bpy.ops.scene.new(type='FULL_COPY')
        if bpy.context.scene == self.original_scene:
            raise Exception('Could not switch to the copied export scene.')
        self.export_scene = bpy.context.scene
        return self

    def remove_export_names(self):
        for id_data in self.named_ids:
            if EXPORT_NAME_PROPERTY in id_data:
                del id_data[EXPORT_NAME_PROPERTY]
        self.named_ids = []

    def remove_export_scene(self, scene = None):
        """Delete a scene and all its objects."""
        self.remove_export_names()

        # Sort out the scene object.
        if scene is None:
            # Not specified: it's the scene created by copy_scene.
            scene = self.export_scene
        else:
            if isinstance(scene, str):
                scene = bpy.data.scenes[scene]

        # never delete the data of the scene we started from
        if scene is None or scene == self.original_scene:
            return

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
        world = scene.world
        if world is not None and world.users <= 1:
            bpy.data.worlds.remove(world)

        # remove collections created by scene duplication
        for coll in set(bpy.data.collections) - self.existing_collections:
            bpy.data.collections.remove(coll)

        # Remove scene.
        bpy.data.scenes.remove(scene, do_unlink=True)
        self.export_scene = None

        # open the scene were we started from
        bpy.context.window.scene = self.original_scene