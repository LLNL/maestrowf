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
            "description:\n    name: hello_world\n    description: A simple "
            "Hello World study.\nenv:\n    variables:\n        "
            "OUTPUT_PATH: \nstudy:\n    - name: hello_world\n      "
            "description: Say hello to the world!\n      run:\n"
            "        cmd: |\n"
            '            echo "Hello, World!" > hello_world.txt\n',
            ValidationError,
            "The value 'None' in field variables",
        ),
        (
            "description:\n  name: hello_world\n  description: A simple "
            "'Hello World' study.\n\nenv:\n  variables:\n    "
            "OUTPUT_PATH: ./sample_output/hello_world\n\n"
            "study:\n  - name: hello_world\n    run:\n      cmd: |\n        "
            'echo "Hello, World!" > hello_world.txt\n',
            ValidationError,
            "Key 'description' is missing from study step",
        ),
        (
            "description:\n  name: hello_world\n  description: A simple "
            "'Hello World' study.\n\nenv:\n  variables:\n    "
            "OUTPUT_PATH: ./sample_output/hello_world\n\n"
            "study:\n",
            ValueError,
            "A study specification MUST contain at least"
            " one step in its workflow",
        ),
        (
            "description:\n  name: hello_world\n  description: A simple "
            "Hello World study.\nenv:\n  variables:\n    "
            "OUTPUT_PATH: ./sample_output/hello_world\n  dependencies:\n    "
            "git:\n      - name: LULESH\n        path: $(OUTPUT_PATH)\n       "
            " url: https://github.com/LLNL/LULESH.git\n      - name: "
            "LULESH\n        path: $(OUTPUT_PATH)\n        "
            "url: https://github.com/LLNL/LULESH.git\nstudy:\n  - name: "
            "hello_world\n    description: yikes\n    run:\n      cmd: |\n"
            '        echo "Hello, World!" > hello_world.txt\n',
            ValueError,
            "Variable name 'LULESH' is already taken",
        ),
    ],
)
def test_validate_error(spec, error, error_txt):
    bspec = str.encode(spec)
    with raises(error) as value_error:
        spec = YAMLSpecification.load_specification_from_stream(bspec)
        assert error_txt in value_error.value
