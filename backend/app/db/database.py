from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings


def _build_url(raw: str) -> str:
    """Convert postgresql:// → postgresql+asyncpg:// and add PgBouncer flag if pooler URL."""
    url = raw
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # PgBouncer transaction mode requires prepared statement cache disabled
    if "pooler.supabase.com" in url and "prepared_statement_cache_size" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}prepared_statement_cache_size=0"
    return url


engine = create_async_engine(
    _build_url(settings.database_url),
    pool_size=5,
    max_overflow=10,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
