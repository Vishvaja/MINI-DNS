# tests/conftest.py

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.storage.db import get_db, AsyncSessionLocal

# Override DB dependency
@pytest.fixture(scope="function")
def override_get_db():
    async def _get_db():
        async with AsyncSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = _get_db

# Return isolated AsyncClient
@pytest.fixture(scope="function")
async def client(override_get_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
