import copy

from packaging.version import Version


def version_replace_fields(version: Version, **kwargs) -> Version:
    version = copy.copy(version)
    version._version = version._version._replace(**kwargs)
    return Version(str(version))
