from typing import Optional

import docker
from docker.models.containers import Container
import argparse

from abc import ABC, abstractmethod


def run_in_container(container: Container, cmd: str, working_dir: Optional[str] = None):
    print('Running command:', cmd)
    _, output_generator = container.exec_run(
        cmd,
        workdir=working_dir,
        stream=True
    )

    for chunk in output_generator:
        print(chunk.decode('utf-8'), end='')


class Source(ABC):

    @abstractmethod
    def prepare_source(self):
        pass

    @property
    @abstractmethod
    def path(self):
        pass


class GitRepoSource(Source):

    def __init__(self, container: Container, repo: str):
        self._container = container
        self._repo = repo
        self._cloned_path = '/source'

    def prepare_source(self):
        print('Cloning git repo', self._repo)
        run_in_container(
            self._container,
            f"git clone {self._repo} {self._cloned_path}"
        )

    @property
    def path(self):
        return self._cloned_path


class HostDirSource(Source):

    def __init__(self, container: Container, host_path: str):
        self._container = container
        self._host_path = host_path

    def prepare_source(self):
        pass

    @property
    def path(self):
        pass


class BuildSystem(ABC):

    @abstractmethod
    def build(self, source: Source):
        pass

    @abstractmethod
    def download_result(self, source: Source, out_dir: str):
        pass


class GradlewBuildSystem(BuildSystem):

    def __init__(self, container: Container, task_name: str, should_clean: bool):
        self._container = container
        self._task_name = task_name
        self._should_clean = should_clean

    def build(self, source: Source):
        print('Running build with gradlew')
        run_in_container(
            self._container,
            f"./gradlew{' clean ' if self._should_clean else ''}{self._task_name}",
            working_dir=source.path
        )
        run_in_container(
            self._container,
            "ls .",
            working_dir=source.path
        )

    def download_result(self, source: Source, out_dir: str):
        print('Downloading build results')

        bits, _ = self._container.get_archive(
            f"{source.path}"
        )

        out_path = f"{out_dir}/result.tar"
        with open(out_path, 'wb') as f:
            for chunk in bits:
                f.write(chunk)

        print('Downloaded to', out_path)


def run(container: Container, args: argparse.Namespace):
    if args.repo:
        print('Building from repo', args.repo)
        source = GitRepoSource(container, args.repo)
    elif args.path:
        print('Building from directory', args.path)
        source = HostDirSource(container, args.path)
    else:
        raise RuntimeError('source not configured')

    if args.gradlew:
        print('Building with gradle wrapper')
        print('\tUsing task', args.gradle_task)
        if args.gradle_clean:
            print('\tCleaning first')

        build_system = GradlewBuildSystem(container, args.gradle_task, args.gradle_clean)
    else:
        raise RuntimeError('build type not selected')

    source.prepare_source()
    build_system.build(source)
    build_system.download_result(source, args.out_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-img',
                        action='store',
                        required=True,
                        help='Name of the image to use for building')

    parser.add_argument('--repo',
                        action='store',
                        type=str,
                        help='Link to the repository to build')
    parser.add_argument('--path',
                        action='store',
                        type=str,
                        help='Path to folder to build')

    parser.add_argument('--out-dir',
                        action='store',
                        type=str,
                        required=True,
                        help='Path to download result into')

    parser.add_argument('--gradlew',
                        action='store_true',
                        default=False,
                        help='Build with gradle wrapper')
    parser.add_argument('--gradle-task',
                        action='store',
                        default='build',
                        help='Name of task to use for building')
    parser.add_argument('--gradle-clean',
                        action='store_true',
                        default=True,
                        help='Whether to clean before building with gradle')

    args = parser.parse_args()

    client = docker.from_env()
    container = client.containers.run(args.base_img,
                                      entrypoint='/bin/sh',
                                      detach=True,
                                      tty=True)
    try:
        run(container, args)
    finally:
        container.stop()
        container.remove()


if __name__ == '__main__':
    main()
