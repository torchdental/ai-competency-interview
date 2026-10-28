from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app import app
from src.common.db import get_session
from src.models.base import Base
from src.models.claim import Claim, ClaimStatus
from src.models.payer import Payer
from src.models.procedure import Procedure

PRACTICE_ID = "practice-1"
PAYER_ID = 1  # first row in a fresh database


@pytest.fixture
async def sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as s:
        s.add(Payer(name="Delta Dental", payer_code="DELTA"))
        await s.commit()
    yield factory
    await engine.dispose()


@pytest.fixture
async def client(sessions: async_sessionmaker[AsyncSession]) -> AsyncIterator[httpx.AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def add_claim(
    sessions: async_sessionmaker[AsyncSession],
    status: ClaimStatus = ClaimStatus.PENDING,
    practice_id: str = PRACTICE_ID,
) -> int:
    async with sessions() as s:
        claim = Claim(
            practice_id=practice_id,
            patient_name="Alice Johnson",
            payer_id=PAYER_ID,
            status=status,
            total_amount=65.00,
            procedures=[Procedure(code="D0120", description="Periodic oral evaluation", amount=65.00)],
        )
        s.add(claim)
        await s.commit()
        return claim.id


async def list_claims(client: httpx.AsyncClient, **params: str) -> dict:
    res = await client.get("/api/claims", params={"practice_id": PRACTICE_ID, **params})
    assert res.status_code == 200
    return res.json()


def claim_payload(*procedures: tuple[str, float]) -> dict:
    return {
        "practice_id": PRACTICE_ID,
        "patient_name": "Alice Johnson",
        "payer_id": PAYER_ID,
        "procedures": [{"code": code, "amount": amount} for code, amount in procedures],
        "total_amount": sum(amount for _, amount in procedures),
    }


# --- Status updates ---


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (ClaimStatus.PENDING, ClaimStatus.VALIDATED),
        (ClaimStatus.PENDING, ClaimStatus.REJECTED),
        (ClaimStatus.VALIDATED, ClaimStatus.ACCEPTED),
        (ClaimStatus.VALIDATED, ClaimStatus.REJECTED),
    ],
)
async def test_status_update_returns_updated_claim(
    client: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    start: ClaimStatus,
    target: ClaimStatus,
) -> None:
    claim_id = await add_claim(sessions, status=start)

    res = await client.patch(
        f"/api/claims/{claim_id}/status",
        params={"practice_id": PRACTICE_ID},
        json={"status": target.value},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == target.value
    assert len(body["procedures"]) == 1
    assert [c["status"] for c in (await list_claims(client))["claims"]] == [target.value]


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (ClaimStatus.PENDING, ClaimStatus.ACCEPTED),
        (ClaimStatus.REJECTED, ClaimStatus.VALIDATED),
        (ClaimStatus.ACCEPTED, ClaimStatus.REJECTED),
    ],
)
async def test_invalid_status_update_returns_400_with_reason(
    client: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    start: ClaimStatus,
    target: ClaimStatus,
) -> None:
    claim_id = await add_claim(sessions, status=start)

    res = await client.patch(
        f"/api/claims/{claim_id}/status",
        params={"practice_id": PRACTICE_ID},
        json={"status": target.value},
    )

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert start.value in detail
    assert target.value in detail
    assert [c["status"] for c in (await list_claims(client))["claims"]] == [start.value]


async def test_status_update_for_other_practice_returns_404(
    client: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    claim_id = await add_claim(sessions, practice_id="practice-2")

    res = await client.patch(
        f"/api/claims/{claim_id}/status",
        params={"practice_id": PRACTICE_ID},
        json={"status": "validated"},
    )

    assert res.status_code == 404


# --- Submission ---


async def test_submitted_claim_appears_in_list(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/claims", json=claim_payload(("D0120", 65.00)))

    assert res.status_code == 200
    claim = res.json()["claim"]
    assert claim["status"] == "pending"
    assert [c["id"] for c in (await list_claims(client))["claims"]] == [claim["id"]]


@pytest.mark.parametrize("code", ["D9999", ""])
async def test_submit_with_unrecognized_code_returns_validation_error(
    client: httpx.AsyncClient, code: str
) -> None:
    res = await client.post("/api/claims", json=claim_payload((code, 65.00)))

    assert res.status_code == 422
    errors = res.json()["detail"]["validation_errors"]
    assert len(errors) == 1
    assert "unrecognized" in errors[0]
    assert (await list_claims(client))["claims"] == []


async def test_submit_over_max_amount_returns_validation_error(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/claims", json=claim_payload(("D0120", 200.00)))

    assert res.status_code == 422
    assert res.json()["detail"]["validation_errors"] == [
        "Procedure D0120: amount $200.00 exceeds maximum $75.00"
    ]


# --- Status filter ---


async def test_list_claims_filters_by_status(
    client: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    pending_id = await add_claim(sessions, status=ClaimStatus.PENDING)
    await add_claim(sessions, status=ClaimStatus.VALIDATED)
    await add_claim(sessions, status=ClaimStatus.REJECTED)
    await add_claim(sessions, status=ClaimStatus.PENDING, practice_id="practice-2")

    assert (await list_claims(client))["total"] == 3

    body = await list_claims(client, status="pending")
    assert [c["id"] for c in body["claims"]] == [pending_id]
    assert body["total"] == 1


async def test_list_claims_with_unknown_status_returns_422(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/claims", params={"practice_id": PRACTICE_ID, "status": "bogus"})

    assert res.status_code == 422
