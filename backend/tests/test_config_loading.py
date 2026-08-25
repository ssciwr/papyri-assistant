"""Cover reading a config file and constructing the objects it asks for."""

from __future__ import annotations

import inspect

import pytest

from papyri_backend.utils import utils


def write(tmp_path, text: str):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


# --- load_config ------------------------------------------------------------


def test_prose_survives_being_loaded(tmp_path) -> None:
    # A prompt is data. Earlier every string was offered to the import machinery,
    # which destroyed any setting that happened to contain dots.
    path = write(tmp_path, 'system_prompt: "You are helpful. Be concise. Cite."\n')

    config = utils.load_config(path)

    assert config["system_prompt"] == "You are helpful. Be concise. Cite."


def test_import_paths_are_resolved_under_type_and_tools(tmp_path) -> None:
    path = write(
        tmp_path,
        "model:\n"
        "  type: langchain_openai.ChatOpenAI\n"
        "tools:\n"
        "  - papyri_backend.tools.sql.query_sql\n",
    )

    config = utils.load_config(path)

    assert inspect.isclass(config["model"]["type"])
    assert config["tools"][0].name == "query_sql"


def test_a_bad_import_path_is_reported(tmp_path) -> None:
    # In these positions a string that does not resolve is a typo, not data.
    # Passing it through would surface much later, as a confusing failure.
    path = write(tmp_path, "tools:\n  - papyri_backend.tools.sql.no_such_tool\n")

    with pytest.raises((ValueError, AttributeError)):
        utils.load_config(path)


def test_environment_variables_are_substituted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOME_URL", "http://example.test/v1")
    path = write(tmp_path, "base_url: ${SOME_URL}\n")

    assert utils.load_config(path)["base_url"] == "http://example.test/v1"


@pytest.mark.parametrize(
    "set_to", [pytest.param(None, id="unset"), pytest.param("", id="empty")]
)
def test_a_fallback_covers_unset_and_empty(tmp_path, monkeypatch, set_to) -> None:
    # An empty value has to count as absent: a compose file forwarding a
    # variable the host never set produces an empty string, not an unset one.
    if set_to is None:
        monkeypatch.delenv("SOME_KEY", raising=False)
    else:
        monkeypatch.setenv("SOME_KEY", set_to)
    path = write(tmp_path, "api_key: ${SOME_KEY:-EMPTY}\n")

    assert utils.load_config(path)["api_key"] == "EMPTY"


def test_a_missing_variable_without_a_fallback_is_reported(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("SOME_KEY", raising=False)
    path = write(tmp_path, "api_key: ${SOME_KEY}\n")

    with pytest.raises(ValueError, match="SOME_KEY"):
        utils.load_config(path)


def test_a_bare_dollar_is_left_alone(tmp_path) -> None:
    path = write(tmp_path, 'prompt: "costs $5, not ${5}"\n')

    assert utils.load_config(path)["prompt"] == "costs $5, not ${5}"


# --- build ------------------------------------------------------------------


class Example:
    def __init__(self, a=None, model=None, **extra):
        self.a, self.model, self.extra = a, model, extra


class NoModel:
    def __init__(self, a=None):
        self.a = a


class Catchall:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_a_spec_is_constructed() -> None:
    built = utils.build({"type": Example, "kwargs": {"a": 1}})

    assert isinstance(built, Example) and built.a == 1


def test_nested_specs_are_constructed() -> None:
    built = utils.build(
        {"type": Example, "kwargs": {"a": {"type": Example, "kwargs": {"a": 2}}}}
    )

    assert isinstance(built.a, Example) and built.a.a == 2


def test_a_mapping_with_type_but_no_kwargs_is_left_as_data() -> None:
    # A json schema carries "type" as ordinary data. Constructing it would turn
    # an argument schema into a broken object.
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}

    assert utils.build({"args_schema": schema}) == {"args_schema": schema}


def test_defaults_reach_a_constructor_that_names_the_argument() -> None:
    built = utils.build({"type": Example, "kwargs": {}}, defaults={"model": "m"})

    assert built.model == "m"


def test_defaults_skip_a_constructor_that_does_not_name_the_argument() -> None:
    built = utils.build({"type": NoModel, "kwargs": {}}, defaults={"model": "m"})

    assert built.a is None


def test_defaults_do_not_ride_in_on_a_kwargs_catchall() -> None:
    # A **kwargs signature accepts every name, so it is no evidence the
    # constructor wants the argument -- passing it in would land it in a
    # deprecation bucket rather than being used.
    built = utils.build({"type": Catchall, "kwargs": {}}, defaults={"model": "m"})

    assert built.kwargs == {}


def test_the_config_wins_over_a_default() -> None:
    built = utils.build(
        {"type": Example, "kwargs": {"model": "explicit"}}, defaults={"model": "m"}
    )

    assert built.model == "explicit"
