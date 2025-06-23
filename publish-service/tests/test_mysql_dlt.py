"""Module containing unit tests for the DLTDataRetriever class."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import logging
from app.core import DLTDataRetriever
from app.schema import DataPackageContract


class TestDLTDataRetriever:
    """Unit tests for the DLTDataRetriever class."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up the test case with necessary data and objects."""
        self.access_payload = DataPackageContract(
            project_name="test_project",
            project_start_time="20250205_010101",
            destination={
                "name": "NW",
                "type": "filestore",
                "format": "csv",
            },
            source={
                "type": "mysql",
                "host_url": "mysql-rfam-public.ebi.ac.uk",
                "database": "Rfam",
                "port": 4497,
                "credentials": {
                    "username_key": "sqlusernamesecretname",
                    "password_key": "sqlpasswordsecretname",
                },
            },
            metadata={
                "schema_name": "Rfam",
                "tables": [
                    {
                        "name": "family",
                        "columns": [
                            {"name": "auto_wiki", "datatype": "integer"},
                            {"name": "noise_cutoff", "datatype": "string"},
                        ],
                    },
                ],
            },
        )
        self.log = logging.getLogger("test_logger")
        self.retriever = DLTDataRetriever(self.access_payload, self.log)

    @patch("app.config.Settings.get_secret")
    def test_mysql_get_table_metadata_success(
        self,
        mock_get_secret: patch,  # type: ignore  # noqa: PGH003
    ) -> None:
        """Test case for successful retrieval of table metadata from public MySQL database."""

        def mock_secret_side_effect(secret_name: str):
            # Mock the responses for both username and password secrets
            if secret_name == "sqlusernamesecretname":
                return MagicMock(get_secret_value=MagicMock(return_value="rfamro"))
            if secret_name == "sqlpasswordsecretname":
                return MagicMock(get_secret_value=MagicMock(return_value=""))
            return None

        mock_get_secret.side_effect = mock_secret_side_effect

        self.retriever._get_source_connection_string()  # noqa: SLF001
        self.retriever._create_sqlalchemy_engine()  # noqa: SLF001

        columns_dict, primary_key_list = self.retriever._get_table_metadata(
            "family",
        )

        assert len(columns_dict) > 0, "No columns were returned by _get_table_metadata."

    def test_get_table_metadata_success(
        self,
    ) -> None:
        # Create a mock connection and cursor
        mock_conn = MagicMock()
        mock_execute = MagicMock()

        # Set up what conn.execute should return for each call
        # First call: column query
        mock_execute.side_effect = [
            [
                MagicMock(column_name="id", data_type="INTEGER", is_nullable="NO"),
                MagicMock(column_name="name", data_type="VARCHAR", is_nullable="YES"),
            ],
            [
                MagicMock(column_name="id"),
            ],  # Second call: primary key query
        ]
        mock_conn.execute = mock_execute

        # Patch the .engine.connect() method to return our mock_conn in a context manager
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.retriever.engine = mock_engine  # Inject mock engine

        columns_dict, primary_key_list = self.retriever._get_table_metadata(
            "test_table",
        )

        assert columns_dict == {
            "id": {"data_type": "INTEGER", "is_nullable": False},
            "name": {"data_type": "VARCHAR", "is_nullable": True},
        }
        assert primary_key_list == ["id"]

    @patch("app.config.Settings.get_secret")
    def test_get_source_connection_string_success(
        self,
        mock_get_secret: patch,  # type: ignore  # noqa: PGH003
    ) -> None:  # type: ignore  # noqa: PGH003
        """Test case for successful construction of connection string."""

        def mock_secret_side_effect(secret_name: str):
            # Mock the responses for both username and password secrets
            if secret_name == "sqlusernamesecretname":
                return MagicMock(get_secret_value=MagicMock(return_value="username"))
            if secret_name == "sqlpasswordsecretname":
                return MagicMock(get_secret_value=MagicMock(return_value="password"))
            return None

        mock_get_secret.side_effect = mock_secret_side_effect

        self.retriever._get_source_connection_string()  # noqa: SLF001

        assert (
            self.retriever.connection_string
            == "mysql+pymysql://username:password@mysql-rfam-public.ebi.ac.uk:4497/Rfam"
        )
