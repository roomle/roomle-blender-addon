import json
import bpy
from pathlib import Path
import sys, os

if True:
    for s in Path('./env').rglob('site-packages'):
        if s.is_dir():
            sys.path.insert(0,str(s.resolve().absolute()))
            break
    import debugpy
    debugpy.listen(('localhost',5678))
    debugpy.wait_for_client()
    # breakpoint()

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

glb, params = sys.argv[sys.argv.index('--')+1:]
bpy.ops.import_scene.gltf(filepath=glb)
bpy.ops.export_mesh.roomle_script(**json.loads(params))