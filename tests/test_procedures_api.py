from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.app import app
from src.common.db import get_session
from src.models.base import Base
from src.models.claim import Claim, ClaimStatus
from src.models.payer import Payer

SessionFactory = async_sessionmaker[AsyncSession]


@pytest.fixture
async def session_factory() -> AsyncIterator[SessionFactory]:
    # StaticPool keeps one in-memory DB shared across the per-request sessions.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as s:
        s.add(Payer(name="Delta Dental", payer_code="DELTA"))
        await s.commit()

    yield factory

    await engine.dispose()


@pytest.fixture
async def client(session_factory: SessionFactory) -> AsyncIterator[httpx.AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def submit_claim(client: httpx.AsyncClient) -> dict:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "Jane Doe",
            "payer_id": 1,
            "procedures": [
                {"code": "D0120", "amount": 65.00},
                {"code": "D0210", "amount": 150.00},
            ],
            "total_amount": 215.00,
        },
    )
    assert response.status_code == 200
    return response.json()["claim"]


async def get_claim(client: httpx.AsyncClient, claim_id: int) -> dict:
    response = await client.get(f"/api/claims/{claim_id}?practice_id=practice-1")
    assert response.status_code == 200
    return response.json()


def procedure_by_code(claim: dict, code: str) -> dict:
    return next(p for p in claim["procedures"] if p["code"] == code)


async def test_void_procedure_returns_claim_with_updated_total(client: httpx.AsyncClient) -> None:
    claim = await submit_claim(client)
    kept = procedure_by_code(claim, "D0120")
    target = procedure_by_code(claim, "D0210")

    response = await client.patch(
        f"/api/procedures/{target['id']}?practice_id=practice-1", json={"voided": True}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == claim["id"]
    assert body["total_amount"] == 65.00
    assert {p["id"]: p["voided"] for p in body["procedures"]} == {
        kept["id"]: False,
        target["id"]: True,
    }


async def test_voided_procedure_is_persisted(client: httpx.AsyncClient) -> None:
    claim = await submit_claim(client)
    target = procedure_by_code(claim, "D0210")

    await client.patch(
        f"/api/procedures/{target['id']}?practice_id=practice-1", json={"voided": True}
    )

    detail = await get_claim(client, claim["id"])
    assert procedure_by_code(detail, "D0210")["voided"] is True
    assert detail["total_amount"] == 65.00


async def test_void_procedure_from_another_practice_returns_404(client: httpx.AsyncClient) -> None:
    claim = await submit_claim(client)
    target = procedure_by_code(claim, "D0210")

    response = await client.patch(
        f"/api/procedures/{target['id']}?practice_id=practice-2", json={"voided": True}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}
    detail = await get_claim(client, claim["id"])
    assert procedure_by_code(detail, "D0210")["voided"] is False


async def test_void_procedure_on_accepted_claim_returns_409(
    client: httpx.AsyncClient, session_factory: SessionFactory
) -> None:
    claim = await submit_claim(client)
    async with session_factory() as s:
        db_claim = await s.get(Claim, claim["id"])
        db_claim.status = ClaimStatus.ACCEPTED
        await s.commit()
    target = procedure_by_code(claim, "D0210")

    response = await client.patch(
        f"/api/procedures/{target['id']}?practice_id=practice-1", json={"voided": True}
    )

    assert response.status_code == 409
    detail = await get_claim(client, claim["id"])
    assert procedure_by_code(detail, "D0210")["voided"] is False
    assert detail["total_amount"] == 215.00


async def test_void_procedure_rejects_voided_false(client: httpx.AsyncClient) -> None:
    claim = await submit_claim(client)
    target = procedure_by_code(claim, "D0210")

    response = await client.patch(
        f"/api/procedures/{target['id']}?practice_id=practice-1", json={"voided": False}
    )

    assert response.status_code == 422
