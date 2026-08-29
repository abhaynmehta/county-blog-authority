"""A YAML loader that refuses to lose data quietly.

Standard `yaml.safe_load` accepts duplicate mapping keys and keeps the last
one. In a fact registry that is the worst possible behaviour: appending a
corrected `pricing:` block leaves the file looking right to a reader while
the loader silently discards one of them, and nothing reports it.

That happened here — clove_county.yaml carried two `configurations:` and two
`pricing:` keys, and the registry served whichever came last.
"""

from __future__ import annotations

from pathlib import Path

import yaml


class DuplicateKeyError(yaml.YAMLError):
    """Raised when a mapping defines the same key twice."""


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that treats a repeated mapping key as an error."""


def _no_duplicates(loader: _StrictLoader, node, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            mark = key_node.start_mark
            raise DuplicateKeyError(
                f"duplicate key {key!r} at line {mark.line + 1}, column "
                f"{mark.column + 1} — the earlier value would be discarded"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates
)


def safe_load(text: str):
    """Parse YAML, raising DuplicateKeyError on a repeated key."""
    return yaml.load(text, Loader=_StrictLoader)


def load_file(path: str | Path):
    """Parse a YAML file with duplicate-key detection."""
    return safe_load(Path(path).read_text(encoding="utf-8"))
