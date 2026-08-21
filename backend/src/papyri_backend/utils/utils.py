import importlib
from typing import Any


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
                if e.name != prefix:
                    raise
                continue

            for attr in parts[i:]:
                obj = getattr(obj, attr)
            return obj

        return path
    else:
        return path


def _process_config(value: Any):
    """_summary_

    Args:
        value (Any): _description_

    Returns:
        _type_: _description_
    """
    if isinstance(value, list):
        result = []
        for element in value:
            result.append(_process_config(element))
        return result

    elif isinstance(value, dict):
        result = {}
        for i in value:
            result[i] = _process_config(
                value[i],
            )
        return result
    else:
        return load_type(value)
