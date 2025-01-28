"""Contains tests for the FastAPI server."""

from fastapi.testclient import TestClient

from app import config, server

client = TestClient(app=server.app)

FORBIDDEN_STATUS_CODE = 403
OK_STATUS_CODE = 200


def test_read_root_no_token() -> None:
    """Test the root endpoint without an access token."""
    response = client.get("/")
    assert response.status_code == FORBIDDEN_STATUS_CODE


def test_read_root() -> None:
    """Test the root endpoint with an access token."""
    response = client.get("/", params={"access_token": config.get_settings().api_key})
    assert response.status_code == OK_STATUS_CODE
    assert response.json() == {"Hello": "World from " + server.app.title}


def test_read_item_no_token() -> None:
    """Test the read item endpoint without an access token."""
    item_id = 1
    response = client.get(
        f"/items/{item_id}",
    )
    assert response.status_code == FORBIDDEN_STATUS_CODE


def test_read_item() -> None:
    """Test the read item endpoint with an access token."""
    item_id = 1
    response = client.get(
        f"/items/{item_id}",
        params={"access_token": config.get_settings().api_key},
    )
    assert response.status_code == OK_STATUS_CODE
    assert response.json() == {"item_id": item_id}


def test_list_items_no_token() -> None:
    """Test the list items endpoint without an access token."""
    response = client.get("/items")
    assert response.status_code == FORBIDDEN_STATUS_CODE


def test_list_items() -> None:
    """Test the list items endpoint with an access token."""
    response = client.get(
        "/items",
        params={"access_token": config.get_settings().api_key},
    )
    assert response.status_code == OK_STATUS_CODE
    assert response.json() == [
        {"item_id": 1, "name": "Item 1"},
        {"item_id": 2, "name": "Item 2"},
        {"item_id": 3, "name": "Item 3"},
    ]


def test_create_item_no_token() -> None:
    """Test the create item endpoint without an access token."""
    response = client.post(
        "/items",
        json={"name": "Test Item"},
    )
    assert response.status_code == FORBIDDEN_STATUS_CODE


def test_create_item() -> None:
    """Test the create item endpoint with an access token."""
    test_item = {"name": "Test Item"}
    response = client.post(
        "/items",
        params={"access_token": config.get_settings().api_key},
        json=test_item,
    )
    assert response.status_code == OK_STATUS_CODE
    assert response.json()["name"] == test_item["name"]
    assert "item_id" in response.json()
