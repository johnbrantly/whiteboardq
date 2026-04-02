import time
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from whiteboardq_server.database import Database
from whiteboardq_server.routes import api, ws


@pytest_asyncio.fixture
async def test_db(tmp_path: Path) -> AsyncGenerator[Database, None]:
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    await db.connect()
    await db.init_db()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def app_client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with temporary database."""
    from whiteboardq_server import database

    # Save original db
    original_db = database.db

    # Use temporary database
    db_path = tmp_path / "test_app.db"
    test_db = Database(db_path)
    await test_db.connect()
    await test_db.init_db()
    database.db = test_db

    # Create a simple app without lifespan for testing
    app = FastAPI()
    app.include_router(api.router)
    app.include_router(ws.router)

    # Set app state for health endpoint
    app.state.start_time = time.time()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await test_db.close()
    database.db = original_db
