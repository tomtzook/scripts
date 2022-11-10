from maven_repo import KnownMavenRepo, \
    MavenRepository, Artifact, NotFoundException
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo',
                        action='store',
                        type=KnownMavenRepo.argparse,
                        choices=list(KnownMavenRepo),
                        help='Repository to query')
    parser.add_argument('--group', '-g',
                        action='store',
                        type=str,
                        help='Group of the wanted artifact')
    parser.add_argument('--name', '-n',
                        action='store',
                        type=str,
                        help='Name of the wanted artifact')
    parser.add_argument('--version', '-v',
                        action='store',
                        type=str,
                        help='Version of the wanted artifact')
    parser.add_argument('--artifact', '-a',
                        action='store',
                        type=str,
                        help='Artifact in the format group:name:version')

    args = parser.parse_args()

    if args.group and args.name:
        if args.version:
            artifact = Artifact(args.group, args.name, args.version)
        else:
            artifact = Artifact(args.group, args.name)
    elif args.artifact:
        artifact = Artifact.from_full(args.artifact)
    else:
        raise RuntimeError('Missing args. Use group+name or artifact')

    repo = MavenRepository(args.repo.value)
    try:
        info = repo.get_metadata(artifact)

        print()
        print('Version:', info.version)
        print('Updated last:', info.last_updated.strftime(r'%d/%m/%Y %H:%M:%S'))
    except NotFoundException as e:
        print()
        print('Artifact', e.artifact, 'not found')
        print('Searched', e.url)


if __name__ == '__main__':
    main()
