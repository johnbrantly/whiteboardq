import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(app_client: AsyncClient):
    """Test health endpoint with database check."""
    response = await app_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["database"] == "ok"
    assert "connected_clients" in data["checks"]


@pytest.mark.asyncio
async def test_get_messages_empty(app_client: AsyncClient):
    """Test getting messages when none exist."""
    response = await app_client.get("/api/messages")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_message(app_client: AsyncClient):
    """Test creating a message via API."""
    response = await app_client.post(
        "/api/messages",
        json={"content": "Test message"},
        headers={"X-Station-Name": "Front-Desk"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Test message"
    assert data["station_name"] == "Front-Desk"
    assert "id" in data
    assert "created_at" in data
    assert "position" in data


@pytest.mark.asyncio
async def test_create_message_missing_header(app_client: AsyncClient):
    """Test creating message without station name header."""
    response = await app_client.post(
        "/api/messages",
        json={"content": "Test message"},
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_messages_after_create(app_client: AsyncClient):
    """Test getting messages after creating one."""
    await app_client.post(
        "/api/messages",
        json={"content": "Message 1"},
        headers={"X-Station-Name": "Station-1"},
    )
    await app_client.post(
        "/api/messages",
        json={"content": "Message 2"},
        headers={"X-Station-Name": "Station-2"},
    )

    response = await app_client.get("/api/messages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["content"] == "Message 1"
    assert data[1]["content"] == "Message 2"


@pytest.mark.asyncio
async def test_move_message(app_client: AsyncClient):
    """Test moving a message."""
    # Create two messages
    resp1 = await app_client.post(
        "/api/messages",
        json={"content": "First"},
        headers={"X-Station-Name": "Station-1"},
    )
    msg1 = resp1.json()

    await app_client.post(
        "/api/messages",
        json={"content": "Second"},
        headers={"X-Station-Name": "Station-2"},
    )

    # Move first message down
    response = await app_client.put(
        f"/api/messages/{msg1['id']}/move",
        params={"direction": "down"},
        headers={"X-Station-Name": "Station-1"},
    )
    assert response.status_code == 200

    # Check order changed
    messages = await app_client.get("/api/messages")
    data = messages.json()
    assert data[0]["content"] == "Second"
    assert data[1]["content"] == "First"


@pytest.mark.asyncio
async def test_move_nonexistent_message(app_client: AsyncClient):
    """Test moving a message that doesn't exist."""
    response = await app_client.put(
        "/api/messages/nonexistent/move",
        params={"direction": "up"},
        headers={"X-Station-Name": "Station-1"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_message(app_client: AsyncClient):
    """Test deleting a message."""
    create_resp = await app_client.post(
        "/api/messages",
        json={"content": "To delete"},
        headers={"X-Station-Name": "Station-1"},
    )
    msg = create_resp.json()

    response = await app_client.delete(
        f"/api/messages/{msg['id']}",
        headers={"X-Station-Name": "Station-2"},
    )
    assert response.status_code == 204

    # Verify deleted
    messages = await app_client.get("/api/messages")
    assert messages.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_message(app_client: AsyncClient):
    """Test deleting a message that doesn't exist."""
    response = await app_client.delete(
        "/api/messages/nonexistent",
        headers={"X-Station-Name": "Station-1"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_restore_message(app_client: AsyncClient):
    """Test restoring a deleted message."""
    create_resp = await app_client.post(
        "/api/messages",
        json={"content": "To restore"},
        headers={"X-Station-Name": "Station-1"},
    )
    msg = create_resp.json()

    await app_client.delete(
        f"/api/messages/{msg['id']}",
        headers={"X-Station-Name": "Station-1"},
    )

    response = await app_client.post(
        f"/api/messages/{msg['id']}/restore",
        headers={"X-Station-Name": "Station-2"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == msg["id"]


@pytest.mark.asyncio
async def test_get_config(app_client: AsyncClient):
    """Test getting config."""
    response = await app_client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "yellow_threshold_minutes" in data
    assert "red_threshold_minutes" in data
    assert "overdue_threshold_minutes" in data


@pytest.mark.asyncio
async def test_update_config(app_client: AsyncClient):
    """Test updating config."""
    response = await app_client.put(
        "/api/config",
        json={
            "yellow_threshold_minutes": 5,
            "red_threshold_minutes": 15,
            "overdue_threshold_minutes": 25,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["yellow_threshold_minutes"] == 5
    assert data["red_threshold_minutes"] == 15
    assert data["overdue_threshold_minutes"] == 25
