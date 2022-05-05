# slap.core.semver

A semver version constraint specifier compatible with [`packaging`][0].

  [0]: https://packaging.pypa.io/
  [1]: https://docs.npmjs.com/about-semantic-versioning#using-semantic-versioning-to-specify-update-types-your-package-can-accept

## Usage

```py
from slap.core.semver.specifier import SemverSpecifier

spec = SemverSpecifier('1.x')
assert str(spec.version_selector.canonical) == "^1.0.0"
assert spec.contains("1.2.3")
assert not spec.contains("0.3.0")
```

The `SemverSpecifier` constructor will raise `packaging.specifier.InvalidSpecifier` if the
specifier string cannot be parsed.

## Behaviour

The version ranges supported by `SemverSpecifier` are [inspired by NPM][1]. Below is a table to
illustrate the behaviour:

| Release | Example |
| ------- | ------- |
| Patch release | `1.0`, `1.0.x`, `~1.0.4` |
| Minor release | `1.0`, `1.x`, `^1.0.4` |
| Major release | `*` or `x` |
| Other | `x.0.4` |

In addition to the NPM semver version ranges, Python version epochs, pre releases, post releases,
dev releases and local versions are supported. To list some examples: `2!^1.0.4`, `~1.0.3.post1`,
`^1.0.4.dev1+gdeadbeef`.

> Note: The remainder fields are not supported in the `x` placeholder format.

## Compatibility

Requires Python 3.6 or higher.
