import pytest
import os


@pytest.fixture
def spec_path():
    def load_spec(file_name):
        dirpath = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirpath, "specification", "test_specs", file_name)

    return load_spec
