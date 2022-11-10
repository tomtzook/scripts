from typing import List
from zipfile import ZipFile, ZipInfo
import os
import tempfile
import shutil
import argparse


def get_bad_content(archive: ZipFile) -> List[ZipInfo]:
    return list(filter(lambda info: not info.is_dir() and os.path.splitext(info.filename)[1] in ('.bmp', '.jpg'),
                       archive.infolist()))


def get_wanted_content(archive: ZipFile) -> List[ZipInfo]:
    return list(filter(lambda info: not info.is_dir() and os.path.splitext(info.filename)[1] not in ('.bmp', '.jpg'),
                       archive.infolist()))


def copy_contents(src: ZipFile, dst: ZipFile):
    for info in get_wanted_content(src):
        data = src.read(info.filename)
        dst.writestr(info, data)


def delete_unwanted(path: str):
    with tempfile.NamedTemporaryFile() as tmp_dst:
        with ZipFile(path, mode='r') as src, \
                ZipFile(tmp_dst.name, mode='w') as dst:
            copy_contents(src, dst)

        shutil.copy(tmp_dst.name, path)


def handle_file(path: str):
    print(path)
    try:
        delete_unwanted(path)
    except Exception as e:
        print('\t', str(e))


def handle_directory(root_path: str):
    for root, dirs, files in os.walk(root_path):
        for name in files:
            if os.path.splitext(name)[1] == '.pak':
                path = os.path.join(root, name)
                handle_file(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files',
                        action='store',
                        type=str,
                        nargs='+',
                        help='Paths to fix. '
                             'If directory, all .pak files inside are recursively handled. '
                             'If not .pak file, ignored.')

    args = parser.parse_args()

    for path in args.files:
        if not os.path.exists(path):
            continue
        elif os.path.isdir(path):
            handle_directory(path)
        elif os.path.splitext(path)[1] == '.pak':
            handle_file(path)


if __name__ == '__main__':
    main()
    #delete_unwanted(r'/home/tomtzook/games/steamlib/steamapps/common/Men of War Assault Squad 2/mods/call of duty ww3 v1.47/resource/entity/vehicle.pak')
    #with ZipFile(r'/home/tomtzook/games/steamlib/steamapps/common/Men of War Assault Squad 2/mods/call of duty ww3 v1.47/resource/entity/- modern/- deco.pak', mode='r') as f:
        #print('\n'.join([info.filename for info in get_bad_content(f)]))
