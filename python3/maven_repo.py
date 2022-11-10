from typing import Optional
import requests
from xml.etree import ElementTree
from collections import namedtuple
from datetime import datetime
from dateutil import tz
import re
import enum

import timehelper


class KnownMavenRepo(enum.Enum):
    CENTRAL = r'https://repo1.maven.org/maven2'
    SONATYPE_SNAPSHOTS = r'https://oss.sonatype.org/content/repositories/snapshots'

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return KnownMavenRepo[s.upper()]
        except KeyError:
            return s


VersionInfo = namedtuple('LatestVersion', 'version,last_updated')


class Artifact(object):
    FULL_FORMAT = re.compile(r'(.*):(.*)(?::(.*))?')

    def __init__(self, group: str, name: str, version: Optional[str] = None):
        self._group = group
        self._name = name
        self._version = version

    @property
    def group(self) -> str:
        return self._group

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> Optional[str]:
        return self._version

    def __repr__(self):
        if self.version:
            return f'{self.group}:{self.name}:{self.version}'
        return f'{self.group}:{self.name}'

    @classmethod
    def from_full(cls, full: str):
        match = cls.FULL_FORMAT.fullmatch(full)
        if match.lastindex == 3:
            return Artifact(match[1], match[2], match[3])
        return Artifact(match[1], match[2])


class NotFoundException(Exception):

    def __init__(self, url: str, artifact: Artifact):
        self._url = url
        self._artifact = artifact

    @property
    def url(self) -> str:
        return self._url

    @property
    def artifact(self) -> Artifact:
        return self._artifact


class MavenRepository(object):

    def __init__(self, url: str):
        self._url = url

    def get_metadata(self, artifact: Artifact) -> VersionInfo:
        response, url = self._request_file(artifact, 'maven-metadata.xml')

        if response.status_code == 200:
            # ok
            if artifact.version:
                return self._parse_version_metadata(response)
            else:
                return self._parse_versions_metadata(response)
        elif response.status_code == 404:
            # not found
            raise NotFoundException(url, artifact)
        else:
            raise EnvironmentError('Returned Error from {}: ({}) {}'.format(
                url,
                response.status_code,
                response.reason
            ))

    def _request_file(self, artifact: Artifact, wanted_file: str):
        url = self._format_url(artifact, wanted_file)
        return requests.get(url), url

    def _format_url(self, artifact: Artifact, wanted_file: str):
        url = self._url
        url += '/' + '/'.join(artifact.group.split('.'))
        url += '/' + artifact.name

        if artifact.version:
            url += '/' + artifact.version

        url += '/' + wanted_file
        return url

    def _parse_version_metadata(self, response: requests.Response) -> VersionInfo:
        tree = ElementTree.fromstring(response.content)
        assert tree.tag == 'metadata'

        versioning = self._find_tag_in_tree(tree, 'versioning')

        version = self._find_tag_in_tree(tree, 'version')

        last_update = self._find_tag_in_tree(versioning, 'lastUpdated')
        last_update = datetime.strptime(last_update.text, r'%Y%m%d%H%M%S')
        last_update = timehelper.convert_timezone(last_update, tz.tzutc())

        return VersionInfo(version.text, last_update)

    def _parse_versions_metadata(self, response: requests.Response) -> VersionInfo:
        print(response.content)
        tree = ElementTree.fromstring(response.content)
        assert tree.tag == 'metadata'

        versioning = self._find_tag_in_tree(tree, 'versioning')
        latest = self._find_tag_in_tree(versioning, 'latest')

        last_update = self._find_tag_in_tree(versioning, 'lastUpdated')
        last_update = datetime.strptime(last_update.text, r'%Y%m%d%H%M%S')
        last_update = timehelper.convert_timezone(last_update, tz.tzutc())

        return VersionInfo(latest.text, last_update)

    def _find_tag_in_tree(self, tree: ElementTree.Element, tag: str) -> ElementTree.Element:
        for child in tree:
            if child.tag == tag:
                return child

        raise RuntimeError('Tag {} not found in tree'.format(
            tag
        ))
