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
