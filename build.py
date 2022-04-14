'''
build the blender plugin in ./dist folder
'''
import shutil
import os
import json
import datetime
from sqlite3 import Timestamp
from hashlib import md5
from pathlib import Path
from io_mesh_roomle import bl_info

PLUGIN_NAME = 'io_mesh_roomle'
VERSION = '.'.join([str(x) for x in bl_info["version"]])
ZIP_FILENAME = f'{PLUGIN_NAME}_{VERSION}'

ROOT_DIR = Path(__file__).parent.absolute()

BUILD_DIR = ROOT_DIR / 'build'
DIST_DIR = ROOT_DIR / 'dist'
SRC_DIR = ROOT_DIR / PLUGIN_NAME
TIMESTAMP = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')


def BUILD():
    '''
    Main build function
    '''
    # create empty build directory
    delete_build_dir()
    BUILD_DIR.mkdir()

    # copy sources to build tree and remove caches
    shutil.copytree(str(SRC_DIR), str(BUILD_DIR/PLUGIN_NAME))
    shutil.rmtree(str(BUILD_DIR/PLUGIN_NAME/'__pycache__'))

    # Check if this version has been built already
    with open('hashes.json', 'r') as f:
        hashes_dict = json.load(f)
        current_contents_hash = hash_contents(src_dir=BUILD_DIR/PLUGIN_NAME)

    # Check existing hashes for current version
    if VERSION in hashes_dict:

        stored_hash, stored_build_time = hashes_dict[VERSION].values()

        print(
            f'ℹ️ Version {VERSION} has already been built on {stored_build_time}')

        if stored_hash == current_contents_hash:
            print('no changes detected ➡ EXIT')
            delete_build_dir()
            exit()

        else:
            print(f'the current sources are different')
            try:
                while True:
                    option = input(f'update version {VERSION} ? (y/n)')
                    if option.lower() == 'y':
                        break
                    elif option.lower() == 'n':
                        print('exit')
                        delete_build_dir()
                        exit()
            except KeyboardInterrupt as _:
                print('clean up...')
                delete_build_dir()
                exit()

    # add current hash data
    hashes_dict[VERSION] = {
        "hash": current_contents_hash,
        "buildTime": TIMESTAMP
    }

    # save the informations back to file
    with open('hashes.json', 'w') as f:
        hashes_dict = json.dump(hashes_dict, f, indent=4)

    # zip the complete build directory
    shutil.make_archive(ZIP_FILENAME, 'zip', str(BUILD_DIR))

    # move zip to final destination
    final_zip_destination = DIST_DIR / f'{ZIP_FILENAME}.zip'

    if final_zip_destination.exists():
        print(f'♻️ replace existing zip file')
        os.remove(str(final_zip_destination))

    shutil.move(f'{ZIP_FILENAME}.zip', str(DIST_DIR))

    delete_build_dir()


def delete_build_dir():
    '''
    delete the build directory and all of it's contents
    '''
    if BUILD_DIR.exists():
        shutil.rmtree(str(BUILD_DIR))


def hash_contents(src_dir: Path):
    '''
    create a hash resulting of the contents of all
    files within a directory
    '''
    file_hashes = []

    # hash individual file contents
    for file in src_dir.rglob('*'):
        md5_hash = md5()
        with open(str(file), "rb") as f:
            content = f.read()
            md5_hash.update(content)
            digest = md5_hash.hexdigest()
            file_hashes.append(f'{file.name} > {digest}')
    
    # create a hash from the combined file hashes
    file_hashes.sort()
    combined_hash = md5(
        '|'.join(file_hashes).encode(encoding='utf-8')
    ).hexdigest()
    return combined_hash


if __name__ == '__main__':
    BUILD()
