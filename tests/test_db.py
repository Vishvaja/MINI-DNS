import pytest
from sqlalchemy import text
from app.storage.db import AsyncSessionLocal

@pytest.mark.asyncio
async def test_db_connection():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
