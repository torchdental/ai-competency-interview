import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.payer import Payer
from src.services.claim_service import ClaimService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def session() -> AsyncSession:  # type: ignore[return]
    engine = create_async_engine(TEST_DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as s:
        yield s

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def claim_service(session: AsyncSession) -> ClaimService:
    return ClaimService(session)


@pytest.fixture
async def payer(session: AsyncSession) -> Payer:
    p = Payer(name="Delta Dental", payer_code="DELTA")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p
