import bpy
import os
import sys
import logging

def export_roomle_script(
    filepath,
    export_normals=False,
    apply_rotations=True,
    mesh_export_option='AUTO'
):
    bpy.ops.export_mesh.roomle_script(
        filepath=filepath,
        catalog_id="test_id",
        export_normals=export_normals,
        apply_rotations=apply_rotations,
        mesh_export_option=mesh_export_option
        #use_selection=False,
        #uv_float_precision=4,
        #normal_float_precision=5
        )

def prepare_content():
    # Wipe scene
    for obj in bpy.context.scene.objects:
        bpy.data.objects.remove(obj)

    # Create plane
    bpy.ops.mesh.primitive_plane_add(
        radius=1,
        calc_uvs=True,
        location=(0,0,0),
        rotation=(0,0,0),
        layers= (True,)+(False,)*19
    )

try:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] # get all args after "--"

    output_dir = argv[0]

    assert os.path.isdir(output_dir)

    test_name = 'test'

    if bpy.data.filepath:
        test_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
    else:
        prepare_content()

    for export_normals in (True,False):
        for apply_rotations in (True,False):
            for mesh_export_option in ('AUTO','EXTERNAL','INTERNAL'):
                out_file = '{}{}_{}_{}.txt'.format(
                    test_name,
                    '_nrm' if export_normals else '',
                    'norot' if export_normals else 'rot',
                    mesh_export_option.lower(),
                    )
                export_roomle_script(
                    os.path.join(output_dir,out_file),
                    export_normals=export_normals,
                    apply_rotations=apply_rotations,
                    mesh_export_option=mesh_export_option
                    )

except Exception as e:
    logging.exception(e)
    sys.exit(-1)
