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


def test_load_spec(spec_path):
    spec = YAMLSpecification.load_specification(spec_path("hello_world.yml"))

    assert spec_path("hello_world.yml") == spec.path
    assert "hello_world" == spec.description["name"] == spec.name
    spec.name = "a_test"
    assert "a_test" == spec.description["name"] == spec.name

    assert (
        "A simple 'Hello World' study."
        == spec.description["description"]
        == spec.desc
    )
    spec.desc = "a test"
    assert "a_test" == spec.description["name"] == spec.name
    assert "a test" == spec.description["description"] == spec.desc

    assert isinstance(spec.environment["variables"], dict)
    assert (
        "./sample_output/hello_world"
        == spec.environment["variables"]["OUTPUT_PATH"]
    )

    assert "./sample_output/hello_world" == spec.output_path

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
def test_validate_error(spec_path, spec, error, error_txt):
    with raises(error) as value_error:
        YAMLSpecification.load_specification(spec_path(spec))
    if value_error.typename == "ValidationError":
        assert error_txt in value_error.value.message
    else:
        assert error_txt in value_error.value.args[0]


@pytest.mark.parametrize(
    "spec, expected",
    [
        (
            "hello_world.yml",
            "./sample_output/hello_world",
        ),
        (
            "empty_output_path.yml",
            "",
        ),
    ],
)
def test_output_path(spec_path, spec, expected):
    spec = YAMLSpecification.load_specification(spec_path(spec))

    assert expected == spec.output_path


def test_get_study_steps(spec_path):
    spec = YAMLSpecification.load_specification(spec_path("hello_world.yml"))
    steps = spec.get_study_steps()

    assert 1 == len(steps)
    assert "hello_world" == steps[0].name
    assert "Say hello to the world!" == steps[0].description


def test_get_parameters(spec_path):
    spec = YAMLSpecification.load_specification(
        spec_path("hello_bye_parameterized.yml")
    )
    params = spec.get_parameters()

    assert params


def test_get_study_environment(spec_path):
    spec = YAMLSpecification.load_specification(
        spec_path("lulesh_sample1_unix.yml")
    )
    study_env = spec.get_study_environment()

    assert study_env
