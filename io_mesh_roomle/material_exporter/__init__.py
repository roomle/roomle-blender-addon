import bpy
from pathlib import Path
from ._exporter import RoomleMaterialExporter
def export_materials(**keywords):
    pass
    r = bpy.ops.scene.new(type='FULL_COPY')
    # scene = bpy.context.scene

    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        obj.select_set(True)
        # obj.name = get_valid_name(obj.name)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.editmode_toggle()

    RoomleMaterialExporter(out_path=Path(keywords['filepath']).parent)