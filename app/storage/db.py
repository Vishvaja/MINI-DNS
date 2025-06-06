from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from contextlib import asynccontextmanager

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create sessionmaker bound to the async engine
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

#Initialize DB 
async def init_db():
    import app.models.record_db 
    async with engine.begin() as conn:
        await conn.run_sync(app.models.record_db.Base.metadata.create_all)
