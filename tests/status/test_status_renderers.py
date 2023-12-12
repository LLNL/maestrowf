import pytest

from maestrowf.utils import csvtable_to_dict
from maestrowf import status_renderer_factory


# Status csv loader
@pytest.fixture(params=["hello_bye_world.csv"])
def load_csv_status(status_csv_path, request):
    with open(status_csv_path(request.param), "r") as status_csv_file:
        status = csvtable_to_dict(status_csv_file)

    return status


@pytest.fixture
def expected_status(status_csv_path):
    """Loads pre-rendered, uncolored status table layouts"""
    def load_expected_status(expected_status_file):
        with open(status_csv_path(expected_status_file), "r") as es_file:
            expected_status = es_file.readlines()

            return ''.join([line for line in expected_status])
    return load_expected_status


@pytest.mark.parametrize(
    "layout, title, expected",
    [
        (
            "flat",
            "Test Study Flat",
            "hello_bye_world_flat_ref.txt",
        ),
        (
            "narrow",
            "Test Study Narrow",
            "hello_bye_world_narrow_ref.txt",
        ),
    ],
)
def test_status_layout(load_csv_status, expected_status,
                       layout, title, expected):
    """Captures status table to string without color codes for verification"""
    expected_status_output = expected_status(expected)
    status_renderer = status_renderer_factory.get_renderer(layout, disable_theme=False, disable_pager=False)
    status_renderer.layout(status_data=load_csv_status,
                           study_title=title)

    assert status_renderer.render_to_str() == expected_status_output
