
from slap.core.semver.specifier import SemverSpecifier
from packaging.specifiers import InvalidSpecifier

import pytest


@pytest.mark.parametrize("specifier", [
    "x",
    "1!x",
    "x.x",
    "x.x.x",
    "1!x.x.x",
    "42",
    "1!42",
    "42.42",
    "1!42.42",
    "42.42.42",
    "1!42.42.42",
    "42",
    "x.42",
    "42.x",
    "x.42.42",
    "1!x.42.42",
    "x.x.42",
    "x.42.x",
    "42.42.x",
    "42.x.x",
])
def test_parse_good_semver_specifier_with_placeholders(specifier: str) -> None:
    SemverSpecifier(specifier)


@pytest.mark.parametrize("specifier", [
    # Cannot specify a prerelease, postrelease or local version in combination with placeholdrs.
    "x.dev1",
    "x.x+foobar",
    "x.x.x.post1",
    # Cannot use placeholders in combination with other operators.
    "^x.42",
    "~1.x.x",
    "^x",
    "*x",
    # Bad format
    "1.0.y",
    "1.0.xx"
    "1.0."
    "1..0.0"
])
def test_parse_bad_semver_specifier_with_placeholders(specifier: str) -> None:
    with pytest.raises(InvalidSpecifier):
        SemverSpecifier(specifier)


@pytest.mark.parametrize("specifier", [
    "*",
    "^10.2.3",
    "1!^10.2.3",
    "~11.2.3",
    "~11.2.3.dev1",
    "~11.2.3+gdeadbeef",
    "11",
    "11.2",
    "11.2.3",
    "11.dev1",
    "11.2.3.dev1",
    "11.2.3.a2+gdeadbeef",
    "42!11.2.3.a2+gdeadbeef",
])
def test_parse_good_semver_specifier_with_operator(specifier: str) -> None:
    SemverSpecifier(specifier)


@pytest.mark.parametrize("specifier", [
    # No epoch on wildcard.
    "1!*",
    # Nothing can follow a major release specifier.
    "*1",
    "*1.0.0",
])
def test_parse_bad_semver_specifier_with_operator(specifier: str) -> None:
    with pytest.raises(InvalidSpecifier):
        SemverSpecifier(specifier)


@pytest.mark.parametrize(["specifier", "canonical"], [
    # Major
    ("*", "*"),
    ("x", "*"),
    # Minor
    ("1", "^1.0.0"),
    ("1!1", "1!^1.0.0"),
    ("1.x", "^1.0.0"),
    ("1!1.x", "1!^1.0.0"),
    ("^1.0.4", "^1.0.4"),
    ("1!^1.0.4", "1!^1.0.4"),
    # Patch
    ("1.0", "~1.0.0"),
    ("1.0.x", "~1.0.0"),
    ("~1.0.4", "~1.0.4"),
    # Explicit version
    ("1.0.4", "1.0.4"),
    ("1.0.4.dev1", "1.0.4.dev1"),
    # Other
    ("1.x.x", "^1.0.0"),
    ("1.x.1", "1.x.1"),
    ("x.1.0", "x.1.0"),
    ("1!x.1.0", "1!x.1.0"),
])
def test_canonical_semver_specifier(specifier: str, canonical: str) -> None:
    assert ''.join(SemverSpecifier(specifier)._canonical_spec) == canonical, f"input: {specifier}"
