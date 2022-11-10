import argparse
import os
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src',
                        action='store',
                        type=str,
                        help='Path to the tree to flatten')
    parser.add_argument('dst',
                        action='store',
                        type=str,
                        help='Path to the place the flattened content into')

    args = parser.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)

    if not src.exists():
        raise RuntimeError('source doesn\'t exist, can\'t copy')
    if dst.exists():
        raise RuntimeError('destination exists, can\'t copy')

    dst.mkdir()

    count = 0
    for root, _, files in os.walk(src):
        for f in files:
            path = os.path.join(root, f)
            shutil.copy(path, dst)
            count += 1

    print(f'Copied {count} files into {str(dst)}')


if __name__ == '__main__':
    main()
