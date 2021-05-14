import pytest

from maestrowf.utils import csvtable_to_dict
from maestrowf import status_renderer_factory
# from pytest import raises

# Reference data sets


# Status csv loader
# @pytest.fixture(params=["hello_bye_all_parameterized.csv",
#                         "hello_bye_all_parameterized_old.csv"])
@pytest.fixture(params=["hello_bye_world.csv"])
def load_csv_status(status_csv_path, request):
    with open(status_csv_path(request.param), "r") as status_csv_file:
        status = csvtable_to_dict(status_csv_file)

    return status


@pytest.fixture(params=["hello_bye_world_flat_ref.txt"])
def load_expected_status(status_csv_path, request):
    with open(status_csv_path(request.param), "r") as expected_status_file:
        expected_status = expected_status_file.readlines()

    return ''.join([line for line in expected_status])


def test_status_layout(load_csv_status, load_expected_status):
    status_renderer = status_renderer_factory.get_renderer('flat')
    status_renderer.layout(status_data=load_csv_status,
                           study_title='Test Study')

    assert status_renderer.render_to_str() == load_expected_status
