from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "sqlite+aiosqlite:///./claims.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    from src.models.base import Base  # noqa: PLC0415
    import src.models.claim  # noqa: PLC0415, F401
    import src.models.payer  # noqa: PLC0415, F401
    import src.models.procedure  # noqa: PLC0415, F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
