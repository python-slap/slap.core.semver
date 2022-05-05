import abc
import enum
import re
from typing import Optional, Tuple

from packaging.specifiers import ParsedVersion, _IndividualSpecifier
from packaging.utils import canonicalize_version
from packaging.version import Version

from .utils import version_replace_fields

__all__ = [
    "SemverSpecifier",
]


def _format_epoch(epoch: Optional[int]) -> str:
    return "" if epoch in (None, 0) else f"{epoch}!"


class VersionSelector(abc.ABC):
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self!s})"

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        ...

    @abc.abstractmethod
    def __hash__(self) -> int:
        ...

    @abc.abstractmethod
    def __str__(self) -> str:
        ...

    @abc.abstractproperty
    def canonical(self) -> "VersionSelector":
        ...

    @abc.abstractproperty
    def spec(self) -> Tuple[str, str]:
        ...


class AnyVersionSelector(VersionSelector):
    def __eq__(self, other: object) -> bool:
        return type(other) is AnyVersionSelector

    def __hash__(self) -> int:
        return hash((type(self), "*"))

    def __str__(self) -> str:
        return "*"

    @property
    def canonical(self) -> "VersionSelector":
        return self

    @property
    def spec(self) -> Tuple[str, str]:
        return "*", ""


class PlaceholderVersionSelector(VersionSelector):
    def __init__(self, epoch: Optional[int], version: str) -> None:
        try:
            parts = tuple(
                "x" if part == "x" else int(part) for part in version.split(".")
            )
        except ValueError:
            raise ValueError(f"Invalid PlaceholderVersionSelector: {version!r}")
        self.epoch = epoch
        self.parts = parts

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PlaceholderVersionSelector) and (
            self.epoch,
            self.parts,
        ) == (other.epoch, other.parts)

    def __hash__(self) -> int:
        return hash((type(self), self.epoch, self.parts))

    def __str__(self) -> str:
        return _format_epoch(self.epoch) + ".".join(map(str, self.parts))

    @property
    def canonical(self) -> "VersionSelector":

        parts = self.parts
        if parts == ("x",):
            return AnyVersionSelector()

        epoch = _format_epoch(self.epoch)

        # Convert "1.x" to "^1.0.0", "1.x.x" to "^1.0.0" and "1.0.x" to "~1.0.0".
        if (len(parts) == 2 and parts[1] == "x") or (
            len(parts) == 3 and parts[1:] == ("x", "x")
        ):
            return PackagingVersionSelector(
                PackagingVersionSelector.Mode.MINOR, Version(f"{epoch}{parts[0]}.0.0")
            )
        elif len(parts) == 3 and parts[1] != "x" and parts[2] == "x":
            return PackagingVersionSelector(
                PackagingVersionSelector.Mode.PATCH,
                Version(f"{epoch}{parts[0]}.{parts[1]}.0"),
            )

        return self

    @property
    def spec(self) -> Tuple[str, str]:
        return "", str(self)


class PackagingVersionSelector(VersionSelector):
    class Mode(enum.Enum):
        MINOR = "^"
        PATCH = "~"
        MAYBE_EXACT = ""

    def __init__(self, mode: Mode, version: Version) -> None:
        assert isinstance(version, Version)
        self.mode = mode
        self.version = version

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PackagingVersionSelector) and (
            self.mode,
            self.version,
        ) == (other.mode, other.version)

    def __hash__(self) -> int:
        return hash((type(self), self.mode, self.version))

    def __str__(self) -> str:
        epoch = _format_epoch(self.version.epoch)
        return (
            f"{epoch}{self.mode.value}{version_replace_fields(self.version, epoch=0)}"
        )

    @property
    def canonical(self) -> "VersionSelector":

        if self.mode == self.Mode.MAYBE_EXACT:
            parts = self.version.public.split(".")

            # Convert "1" to "^1.0.0" and "1.0" to "~1.0.0".
            if len(self.version.release) == 1:
                new_version = version_replace_fields(
                    self.version, release=self.version.release + (0, 0)
                )
                return PackagingVersionSelector(self.Mode.MINOR, new_version)
            elif len(parts) == 2:
                new_version = version_replace_fields(
                    self.version, release=self.version.release + (0,)
                )
                return PackagingVersionSelector(self.Mode.PATCH, new_version)

        return PackagingVersionSelector(
            self.mode, Version(canonicalize_version(self.version))
        )

    @property
    def spec(self) -> Tuple[str, str]:
        return self.mode.value, str(self.version)


class SemverSpecifier(_IndividualSpecifier):

    _regex_str = r"""
        # epoch, can not be combined with wildcards. although the epoch must be placed before the operator,
        # we encode in the second spec element.
        (?P<epoch>\d+!(?=\^|~|)(?!\*))?
        (?P<operator>\^|~|\*|)
        (?P<version>
            (?:
                (?:
                    (?<=\*)
                ) |
                (?:
                    (?<!\*)
                    (?:
                        (?P<final>(?:\d+\.){0,2}\d+)

                        # Can be followed by pre- and postrelease information.
                        (?P<remainder>
                            (?P<prelease>                   # pre release
                                [-_\.]?
                                (?:a|b|c|rc|alpha|beta|pre|preview)
                                [-_\.]?
                                [0-9]*
                            )?
                            (?P<postrelease>                   # post release
                                (?:-[0-9]+)|(?:[-_\.]?(?:post|rev|r)[-_\.]?[0-9]*)
                            )?
                            (?P<devrelease>
                                (?:[-_\.]?dev[-_\.]?[0-9]*)?         # dev release
                                (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)? # local
                            )?
                        )
                    ) |
                    (?P<placeholder>
                        # Allow placeholders; only when no operator was specified.
                        (?<!\^|~|\*)
                        (?:(?:\d+|x)\.){0,2}(?:\d+|x)
                    )
                )
            )
        )
    """

    def __init__(self, spec: str = "", prereleases: Optional[bool] = None) -> None:
        super().__init__(spec, prereleases)

        # Re-run the regex, save it for later and encode the epoch in the spec.
        match = self._regex.search(spec)
        assert match is not None
        if match.group("epoch"):
            self._spec = (self._spec[0], match.group("epoch") + self._spec[1])
        self._match = match

        # Identify the version selector that resembles the specifier.
        version_selector: VersionSelector
        if match.group("placeholder"):
            parsed_epoch = (
                int(match.group("epoch")[:-1]) if match.group("epoch") else None
            )
            version_selector = PlaceholderVersionSelector(
                parsed_epoch, match.group("placeholder")
            )
        else:
            epoch = match.group("epoch") or ""
            if match.group("operator") == "*":
                assert not epoch
                version_selector = AnyVersionSelector()
            else:
                version_selector = PackagingVersionSelector(
                    PackagingVersionSelector.Mode(match.group("operator")),
                    Version(epoch + match.group("version")),
                )
        self._version_selector = version_selector

    def _compare_minor(self, prospective: ParsedVersion, spec: str) -> bool:
        raise NotImplementedError

    def _compare_patch(self, prospective: ParsedVersion, spec: str) -> bool:
        raise NotImplementedError

    def _compare_placeholder(self, prospective: ParsedVersion, spec: str) -> bool:
        raise NotImplementedError

    @property
    def version_selector(self) -> VersionSelector:
        return self._version_selector

    # _IndividualSpecifier

    _regex = re.compile(r"^\s*" + _regex_str + r"\s*$", re.VERBOSE | re.IGNORECASE)

    _operators = {
        "^": "minor",
        "~": "patch",
        "": "placeholder",
    }

    @property
    def _canonical_spec(self) -> Tuple[str, str]:
        return self._version_selector.canonical.spec
