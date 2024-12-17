import pandas as pd
import pytest
from prefect.testing.utilities import prefect_test_harness
from pytest_mock import MockerFixture
from md_dataset.file_manager import FileManager
from md_dataset.models.types import DatasetType
from md_dataset.models.types import InputDatasetTable
from md_dataset.models.types import InputParams
from md_dataset.models.types import IntensityInputDataset
from md_dataset.models.types import IntensityTableType
from md_dataset.process import md_py


@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture():
    with prefect_test_harness():
        yield


@pytest.fixture
def fake_file_manager(mocker: MockerFixture):
    file_manager = mocker.Mock(spec=FileManager)

    mocker.patch("md_dataset.process.get_file_manager", return_value=file_manager)
    return file_manager


@pytest.fixture
def input_datasets() -> list[IntensityInputDataset]:
    return [IntensityInputDataset(name="one", tables=[
            InputDatasetTable(name="Protein_Intensity", bucket = "bucket", key = "baz/qux"),
            InputDatasetTable(name="Protein_Metadata", bucket= "bucket", key = "qux/quux"),
        ])]


class TestBlahParams(InputParams):
    id: int

@pytest.fixture
def test_params() -> TestBlahParams:
    return TestBlahParams(dataset_name="foo", id=123)

@md_py
def run_process_sets_name_and_type(input_datasets: list[IntensityInputDataset], params: InputParams, \
        output_dataset_type: DatasetType) -> dict: # noqa: ARG001

    intensity_table = input_datasets[0].table(IntensityTableType.INTENSITY)
    metadata_table = input_datasets[0].table(IntensityTableType.METADATA)
    return {IntensityTableType.INTENSITY.value: intensity_table.data, \
            IntensityTableType.METADATA.value: metadata_table.data}

def test_run_process_sets_name_and_type(input_datasets: list[IntensityInputDataset], test_params: TestBlahParams, \
        fake_file_manager: FileManager):
    test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    fake_file_manager.load_parquet_to_df.return_value = test_data

    result = run_process_sets_name_and_type(input_datasets, test_params, DatasetType.INTENSITY)
    assert result["name"] == "foo"
    assert result["type"] == DatasetType.INTENSITY

def test_run_process_has_tables(input_datasets: list[IntensityInputDataset], test_params: TestBlahParams, \
        fake_file_manager: FileManager):
    test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    fake_file_manager.load_parquet_to_df.return_value = test_data

    result = run_process_sets_name_and_type(input_datasets, test_params, DatasetType.INTENSITY)
    assert result["tables"][0]["name"] == "Protein_Intensity"
    assert result["tables"][1]["name"] == "Protein_Metadata"

def test_run_process_sets_default_name(input_datasets: list[IntensityInputDataset], \
        fake_file_manager: FileManager):
    test_params = TestBlahParams(id=123)
    test_data = pd.DataFrame({})
    fake_file_manager.load_parquet_to_df.return_value = test_data

    result = run_process_sets_name_and_type(input_datasets, test_params, DatasetType.INTENSITY)
    assert result["name"] == "one"

@md_py
def run_process_data(input_datasets: list[IntensityInputDataset], params: InputParams, \
        output_dataset_type: DatasetType) -> dict: # noqa: ARG001

    intensity_table = input_datasets[0].table(IntensityTableType.INTENSITY)
    metadata_table = input_datasets[0].table(IntensityTableType.METADATA)

    return {IntensityTableType.INTENSITY.value: intensity_table.data.iloc[::-1], \
            IntensityTableType.METADATA.value: metadata_table.data}

def test_run_process_save_and_returns_data(input_datasets: list[IntensityInputDataset], test_params: TestBlahParams, \
        fake_file_manager: FileManager):

    test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    test_metadata = pd.DataFrame({"col1": [4, 5, 6], "col2": ["x", "y", "z"]})
    fake_file_manager.load_parquet_to_df.side_effect = [test_data, test_metadata]

    result = run_process_data(input_datasets, test_params, DatasetType.INTENSITY)

    assert result["tables"][0]["name"] == "Protein_Intensity"
    assert result["tables"][0]["path"] == f"job_runs/{result['run_id']}/intensity.parquet"

    assert result["tables"][1]["name"] == "Protein_Metadata"
    assert result["tables"][1]["path"] == f"job_runs/{result['run_id']}/metadata.parquet"

    fake_file_manager.save_tables.assert_called_once()
    args, _ = fake_file_manager.save_tables.call_args

    assert isinstance(args[0], list)
    assert len(args[0]) == 2 # noqa: PLR2004

    assert args[0][0][0] == f"job_runs/{result['run_id']}/intensity.parquet"
    pd.testing.assert_frame_equal(args[0][0][1], test_data.iloc[::-1])

    assert args[0][1][0] == f"job_runs/{result['run_id']}/metadata.parquet"
    pd.testing.assert_frame_equal(args[0][1][1], test_metadata)

@md_py
def run_process_invalid(input_datasets: list[IntensityInputDataset], params: InputParams, \
        output_dataset_type: DatasetType) -> dict: # noqa: ARG001

    intensity_table = input_datasets[0].table(IntensityTableType.INTENSITY)
    return {IntensityTableType.INTENSITY.value: intensity_table.data}

def test_run_process_invalid(input_datasets: list[IntensityInputDataset], test_params: TestBlahParams, \
        fake_file_manager: FileManager):
    test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    fake_file_manager.load_parquet_to_df.return_value = test_data

    with pytest.raises(Exception) as exception_info:
        run_process_invalid(input_datasets, test_params, DatasetType.INTENSITY)

    assert "1 validation error for IntensityDataset" in str(exception_info.value)
    assert "metadata" in str(exception_info.value)
    assert "field required" in str(exception_info.value)
