import os

import pytest
from jsonschema import ValidationError
from pytest import raises

from maestrowf.specification import YAMLSpecification


def test_create():
    spec = YAMLSpecification()
    assert "" == spec.path
    assert isinstance(spec.description, dict)
    assert isinstance(spec.environment, dict)
    assert isinstance(spec.batch, dict)
    assert isinstance(spec.study, list)
    assert isinstance(spec.globals, dict)


def test_load_spec_error():
    with raises(Exception):
        YAMLSpecification.load_specification("badspec.yaml")


def test_load_spec():
    spec = YAMLSpecification.load_specification(
        "samples/hello_world/hello_world.yaml"
    )
    assert "samples/hello_world/hello_world.yaml" == spec.path
    assert "hello_world" == spec.description["name"] == spec.name
    assert (
        "A simple 'Hello World' study."
        == spec.description["description"]
        == spec.desc
    )

    assert isinstance(spec.environment["variables"], dict)
    assert (
        "./sample_output/hello_world"
        == spec.environment["variables"]["OUTPUT_PATH"]
    )

    assert 1 == len(spec.study)
    assert "hello_world" == spec.study[0]["name"]
    assert "Say hello to the world!" == spec.study[0]["description"]
    assert (
        'echo "Hello, World!" > hello_world.txt\n'
        == spec.study[0]["run"]["cmd"]
    )


@pytest.mark.parametrize(
    "spec, error, error_txt",
    [
        (
            "empty_variables.yml",
            ValidationError,
            "The value 'None' in field variables",
        ),
        (
            "missing_step_desc.yml",
            ValidationError,
            "Key 'description' is missing from study step",
        ),
        (
            "missing_step.yml",
            ValueError,
            "A study specification MUST contain at least"
            " one step in its workflow",
        ),
        (
            "duplicate_dependency.yml",
            ValueError,
            "Variable name 'LULESH' is already taken",
        ),
        (
            "error_parameterized.yml",
            ValidationError,
            "In global.params.GREETING2, label must be of type 'string'",
        ),
        (
            "extra_study_params.yml",
            ValidationError,
            "Unrecognized key 'bad' found in study step",
        ),
    ],
)
def test_validate_error(spec, error, error_txt):
    dirpath = os.path.dirname(os.path.abspath(__file__))
    spec_path = os.path.join(dirpath, "test_specs", spec)
    with raises(error) as value_error:
        spec = YAMLSpecification.load_specification(spec_path)
    if value_error.typename == "ValidationError":
        assert error_txt in value_error.value.message
    else:
        assert error_txt in value_error.value.args[0]
