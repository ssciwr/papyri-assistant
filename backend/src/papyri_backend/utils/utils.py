import importlib
import inspect
import os
import re
from pathlib import Path
from typing import Any

import yaml

# ${VAR} and ${VAR:-fallback}. The braces are required so that a bare "$" in a
# prompt is left alone.
_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

# Config keys whose string values name something to import. Everything else in a
# config is data, including prose that happens to contain dots.
_IMPORT_KEYS = frozenset({"type", "tools"})


def load_type(path: Any) -> Any:
    """Resolve a dotted import path to the object it identifies.

    Args:
        path (Any): Dotted path, e.g. ``"sklearn.metrics.f1_score"`` or
            ``"package.module.Object"`` in case it's a string. In all other cases,
            will be passed through as is

    Raises:
        ModuleNotFoundError: If the path does not identify an available module.
        AttributeError: If a named object does not exist within the module.

    Returns:
        type: The type or callable named by ``path``.
    """
    if isinstance(path, str):
        parts = path.split(".")
        for i in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:i])
            try:
                obj = importlib.import_module(prefix)
            except ModuleNotFoundError as e:
                # Only keep shortening when *this* prefix is what's missing; a
                # module that exists but fails on its own imports must surface as
                # itself instead of being masked by a shorter, unrelated prefix.
                #
                # The missing name reported for "a.b.c" is "a", not "a.b.c" --
                # importlib names the first component it could not find. So the
                # prefix is the thing that is missing when the reported name is
                # the prefix itself or a leading part of it. Comparing the two
                # for equality instead made every string with two or more dots
                # raise, which destroyed any prose setting it was applied to.
                if e.name is None or not (
                    prefix == e.name or prefix.startswith(f"{e.name}.")
                ):
                    raise
                continue

            for attr in parts[i:]:
                obj = getattr(obj, attr)
            return obj

        return path
    else:
        return path


def _expand(text: str) -> str:
    """Substitute environment variables and a leading ``~`` into a config string.

    Args:
        text: A string value read from a config file.

    Returns:
        The string with ``${VAR}`` and ``${VAR:-fallback}`` replaced and a
        leading ``~/`` expanded to the home directory.

    Raises:
        ValueError: A variable without a fallback is unset or empty.
    """

    def replace(match: re.Match[str]) -> str:
        name, fallback = match.group(1), match.group(2)
        # Colon-minus semantics, as in the shell: an empty value counts as
        # unset, which is what a compose file that passes an unset variable
        # through produces.
        value = os.getenv(name) or fallback
        if value is None:
            raise ValueError(
                f"{name} is used in the config but is not set. Set it, or give a "
                f"fallback as ${{{name}:-fallback}}."
            )
        return value

    return os.path.expanduser(_VARIABLE.sub(replace, text))


def _resolve(value: Any, key: str | None = None) -> Any:
    """Expand a loaded config and turn its import paths into objects."""
    if isinstance(value, dict):
        return {k: _resolve(v, k) for k, v in value.items()}

    # A list inherits its key so that the entries of "tools:" are each treated
    # as an import path.
    if isinstance(value, list):
        return [_resolve(v, key) for v in value]

    if isinstance(value, str):
        expanded = _expand(value)
        if key not in _IMPORT_KEYS:
            return expanded
        resolved = load_type(expanded)
        # load_type reports "not an import path" by handing the string back,
        # which in one of these positions means the path is wrong.
        if isinstance(resolved, str):
            raise ValueError(f"{expanded!r} under {key!r} is not an import path.")
        return resolved

    return value


def load_config(path: str | Path) -> dict[str, Any]:
    """Read a yaml config and resolve the import paths in it.

    Args:
        path: Path to the config file.

    Returns:
        The config, with environment variables substituted and dotted paths
        under ``type`` and ``tools`` replaced by the objects they name.

    Raises:
        ValueError: A variable is unset, or a path does not name an object.
    """
    return _resolve(yaml.safe_load(Path(path).resolve().read_text()))


def _is_spec(value: dict[str, Any]) -> bool:
    """Report whether a mapping asks for an object to be constructed."""
    # Both keys are required, so that a json schema -- which carries "type" as
    # ordinary data -- is left as the data it is.
    return "type" in value and "kwargs" in value and callable(value["type"])


def build(value: Any, defaults: dict[str, Any] | None = None) -> Any:
    """Construct the objects a resolved config asks for.

    Args:
        value: A resolved config, or any part of one. Mappings carrying both
            ``type`` and ``kwargs`` are constructed; everything else is walked
            and returned in the shape it came in.
        defaults: Arguments to pass to any constructor that accepts them by
            name and was not given them by the config.

    Returns:
        The value with its specs replaced by constructed objects.
    """
    if isinstance(value, list):
        return [build(item, defaults) for item in value]

    if not isinstance(value, dict):
        return value

    if not _is_spec(value):
        return {k: build(v, defaults) for k, v in value.items()}

    factory = value["type"]
    kwargs = {k: build(v, defaults) for k, v in (value["kwargs"] or {}).items()}

    for name, default in (defaults or {}).items():
        if name in kwargs:
            continue
        parameter = inspect.signature(factory).parameters.get(name)
        # A **kwargs catch-all accepts every name, so it is not evidence that
        # this constructor wants the argument.
        if parameter is not None and parameter.kind is not parameter.VAR_KEYWORD:
            kwargs[name] = default

    return factory(**kwargs)
