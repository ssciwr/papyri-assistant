"""Cover the dotted-path resolver every config value is currently passed through.

``load_type`` is the single point where a config string becomes a Python object,
so its behaviour on strings that are *not* import paths is what decides whether
an ordinary prose setting survives being loaded.
"""

from __future__ import annotations

import os.path

import pytest

from papyri_backend.utils import utils


def test_load_type_resolves_a_dotted_path_to_its_object() -> None:
    # The reason the resolver exists: a config names a callable and gets it.
    assert utils.load_type("os.path.join") is os.path.join


def test_load_type_resolves_a_module() -> None:
    assert utils.load_type("os.path") is os.path


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("x.y", id="one-dot"),
        pytest.param("a.b.c", id="two-dots"),
        pytest.param("1.0.0", id="version-string"),
        pytest.param(
            "You are a helpful assistant. You know how to search. Be concise.",
            id="prose-with-periods",
        ),
        pytest.param("Qwen/Qwen3-Embedding-8B", id="model-name"),
    ],
)
def test_load_type_passes_through_strings_that_are_not_import_paths(value: str) -> None:
    # A config is mostly data: prompts, model names, version strings. Anything
    # the resolver cannot import has to come back unchanged, or the setting is
    # destroyed by being read. The multi-dot cases are the ones that matter --
    # a single-dot string already survives, which is why this went unnoticed
    # until a system prompt grew a second sentence.
    assert utils.load_type(value) == value


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(3, id="int"),
        pytest.param(None, id="none"),
        pytest.param({"k": "v"}, id="dict"),
    ],
)
def test_load_type_passes_non_strings_through(value: object) -> None:
    # Only strings can name an import path; everything else is already a value.
    assert utils.load_type(value) is value


def test_load_type_raises_for_a_missing_attribute_on_a_real_module() -> None:
    # The module resolves, so the string really was an import path and the
    # caller really did mean to name something in it. Passing it through as a
    # string would hide the typo until the object was used.
    with pytest.raises(AttributeError):
        utils.load_type("papyri_backend.utils.utils.does_not_exist")


def test_load_type_reports_a_module_that_fails_on_its_own_imports(
    tmp_path, monkeypatch
) -> None:
    # A module that exists but raises ModuleNotFoundError from *inside itself*
    # must surface as itself. Shortening the path and reporting the shorter,
    # unrelated name would send the reader hunting for the wrong module. This
    # is what the guard in load_type's shortening loop protects, so it is
    # pinned before that guard is touched.
    (tmp_path / "brokenmod.py").write_text("import definitely_not_a_real_module\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(ModuleNotFoundError) as excinfo:
        utils.load_type("brokenmod.Thing")

    assert excinfo.value.name == "definitely_not_a_real_module"
