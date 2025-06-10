"""Module containing unit tests for the DLTDataRetriever class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import logging
from app.dlt import DLTDataRetriever
from app.schema import DataPackageContract


class TestDLTDataRetriever:
    """Unit tests for the DLTDataRetriever class."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up the test case with necessary data and objects."""
        self.access_payload = DataPackageContract(
            project_name="test_project",
            project_start_time="20250205_010101",
            destination_type="NW",
            destination_format="CSV",
            source={
                "type": "DatabricksSQL",
                "host_url": "https://example.com",
                "http_path": "/sql/1.0/endpoints/abc",
                "catalog": "test_catalog",
            },
            credentials={
                "spn_clientid": "databricksspnclientid",
                "spn_secret": "databricksspnsecret",
            },
            metadata={
                "schema_name": "test_schema",
                "tables": [
                    {
                        "name": "test_table",
                        "columns": [
                            {"name": "id", "datatype": "integer"},
                            {"name": "name", "datatype": "string"},
                        ],
                    },
                ],
            },
        )
        self.log = logging.getLogger("test_logger")
        self.retriever = DLTDataRetriever(self.access_payload, self.log)

    @patch("app.dlt.databricks.handle_restapi_request")
    def test_get_table_metadata_success(
        self,
        mock_handle_restapi_request: patch,  # type: ignore  # noqa: PGH003
    ) -> None:
        """Test case for successful retrieval of table metadata."""
        mock_response = {
            "columns": [
                {"name": "id", "type_name": "INTEGER", "nullable": False},
                {"name": "name", "type_name": "STRING", "nullable": True},
            ],
            "table_constraints": [
                {"primary_key_constraint": {"child_columns": ["id"]}},
            ],
        }
        mock_handle_restapi_request.return_value = mock_response

        columns_dict, primary_key_list = self.retriever._get_table_metadata(  # noqa: SLF001
            "test_table",
        )

        assert columns_dict == {
            "id": {
                "name": "id",
                "type_name": "INTEGER",
                "nullable": False,
                "data_type": "INTEGER",
                "is_nullable": False,
            },
            "name": {
                "name": "name",
                "type_name": "STRING",
                "nullable": True,
                "data_type": "STRING",
                "is_nullable": True,
            },
        }
        assert primary_key_list == ["id"]

    @patch("app.dlt.databricks.handle_restapi_request")
    def test_get_table_metadata_invalid_response(
        self,
        mock_handle_restapi_request: patch,  # type: ignore  # noqa: PGH003
    ) -> None:
        """Test case for handling invalid response when retrieving table metadata."""
        mock_handle_restapi_request.return_value = None

        with pytest.raises(AttributeError):
            self.retriever._get_table_metadata("test_table")  # noqa: SLF001

    @patch("app.dlt.databricks.get_access_token")
    def test_get_source_connection_string_success(
        self,
        mock_get_access_token: patch,
    ) -> None:  # type: ignore  # noqa: PGH003
        """Test case for successful construction of connection string."""
        mock_get_access_token.return_value = "test_token"

        self.retriever._get_source_connection_string()  # noqa: SLF001

        assert self.retriever.access_token == "test_token"
        assert (
            self.retriever.connection_string
            == "databricks://token:test_token@example.com?http_path=/sql/1.0/endpoints/abc&catalog=test_catalog"
        )

    @patch("app.dlt.create_engine")
    def test_create_sqlalchemy_engine_success(self, mock_create_engine: patch) -> None:  # type: ignore  # noqa: PGH003
        """Test case for successful creation of SQLAlchemy engine."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        self.retriever.connection_string = "test_connection_string"
        self.retriever._create_sqlalchemy_engine()  # noqa: SLF001

        assert self.retriever.engine == mock_engine
        mock_create_engine.assert_called_once_with("test_connection_string")

    @patch("app.dlt.create_engine")
    def test_create_sqlalchemy_engine_failure(self, mock_create_engine: patch) -> None:  # type: ignore  # noqa: PGH003
        """Test case for failure in creating SQLAlchemy engine."""
        mock_create_engine.side_effect = Exception("Engine creation failed")

        self.retriever.connection_string = "test_connection_string"

        with pytest.raises(
            RuntimeError,
            match="Faileddd to create SQLAlchemy engine: Engine creation failed",
        ):
            self.retriever._create_sqlalchemy_engine()  # noqa: SLF001

    @patch("shutil.rmtree")
    def test_clear_staging_directory_success(self, mock_rmtree: patch) -> None:  # type: ignore  # noqa: PGH003
        """Test case for successful clearing of staging directory."""
        self.retriever.staging_target_path = MagicMock()
        self.retriever.staging_target_path.exists.return_value = True

        self.retriever._clear_staging_directory()  # noqa: SLF001

        mock_rmtree.assert_called_once_with(self.retriever.staging_target_path)
        self.retriever.staging_target_path.mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )

    @patch("shutil.rmtree")
    def test_clear_staging_directory_failure(self, mock_rmtree: patch) -> None:  # type: ignore  # noqa: PGH003
        """Test case for failure in clearing staging directory."""
        self.retriever.staging_target_path = MagicMock()
        self.retriever.staging_target_path.exists.return_value = True
        mock_rmtree.side_effect = OSError("Failed to remove directory")

        with pytest.raises(
            OSError,
            match="Failure clearing staging directory: Failed to remove directory",
        ):
            self.retriever._clear_staging_directory()  # noqa: SLF001

    @patch("dlt.pipeline")
    @patch("dlt.destinations.filesystem")
    @patch("app.utils.get_target_paths")
    def test_initialize_dlt_pipeline_success(
        self,
        mock_get_target_paths: patch,  # type: ignore  # noqa: PGH003
        mock_filesystem: patch,  # type: ignore  # noqa: PGH003
        mock_pipeline: patch,  # type: ignore  # noqa: PGH003
    ) -> None:
        """Test case for successful initialization of DLT pipeline."""
        mock_get_target_paths.return_value = (
            Path("/staging"),
            Path("/production"),
            None,
            None,
            None,
        )
        mock_filesystem.return_value = "filesystem_destination"
        mock_pipeline.return_value = "dlt_pipeline"

        self.retriever._initialize_dlt_pipeline()  # noqa: SLF001

        assert self.retriever.dlt_destination == "filesystem_destination"
        assert self.retriever.pipeline == "dlt_pipeline"
        assert self.retriever.loader_file_format == "csv"

    @patch("app.utils.get_target_paths")
    def test_initialize_dlt_pipeline_unsupported_destination(
        self,
        mock_get_target_paths: patch,  # type: ignore  # noqa: PGH003
    ) -> None:
        """Test case for unsupported destination type when initializing DLT pipeline."""
        mock_get_target_paths.return_value = (
            Path("/staging"),
            Path("/production"),
            None,
            None,
            None,
        )
        self.retriever.destination_format = "UnsupportedType"

        with pytest.raises(
            ValueError,
            match="Unsupported destination format. Only CSV and DUCKDB are supported.",
        ):
            self.retriever._initialize_dlt_pipeline()  # noqa: SLF001
