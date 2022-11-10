from pathlib import Path
from typing import List
from collections import namedtuple

from lxml import etree


Configuration = namedtuple('Configuration', 'name,platform')


class VSProject(object):

    def __init__(self, path: Path):
        self._tree = etree.parse(str(path))
        self._namespaces = {'ns': 'http://schemas.microsoft.com/developer/msbuild/2003'}
        # import property files

    @property
    def configurations(self) -> List[Configuration]:
        configurations = [
            conf
            for conf in self._tree.xpath('//ns:ProjectConfiguration', namespaces=self._namespaces)
        ]
        return [self._parse_configuration(conf) for conf in configurations]

    def _parse_configuration(self, element) -> Configuration:
        name = element.xpath('//ns:Configuration', namespaces=self._namespaces)
        if len(name) == 1:
            name = name[0].text
        else:
            raise ValueError()

        platform = element.xpath('//ns:Platform', namespaces=self._namespaces)
        if len(platform) == 1:
            platform = platform[0].text
        else:
            platform = None

        return Configuration(name, platform)


PATH = Path(r"/home/tomtzook/git/VisualUefi/EDK-II/UefiLib/UefiLib.vcxproj")
project = VSProject(PATH)
print(project.configurations)
