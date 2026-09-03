import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.payer import Payer


@pytest.fixture
async def cigna_payer(session: AsyncSession) -> Payer:
    p = Payer(name="Cigna", payer_code="CIG001")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


async def test_create_claim_with_new_code(client: AsyncClient, payer: Payer) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": payer.id,
            "procedures": [{"code": "D1110", "description": "Prophy", "amount": 110.00}],
            "total_amount": 110.00,
        },
    )
    assert response.status_code == 200


async def test_create_claim_restricted_code_for_allowed_payer(
    client: AsyncClient, payer: Payer
) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": payer.id,
            "procedures": [{"code": "D3310", "description": "Endo", "amount": 750.00}],
            "total_amount": 750.00,
        },
    )
    assert response.status_code == 200


async def test_create_claim_restricted_code_for_other_payer_is_422(
    client: AsyncClient, cigna_payer: Payer
) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": cigna_payer.id,
            "procedures": [{"code": "D3310", "description": "Endo", "amount": 750.00}],
            "total_amount": 750.00,
        },
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["validation_errors"]
    assert any("D3310" in e and "CIG001" in e for e in errors)


async def test_create_claim_unrestricted_code_for_any_payer(
    client: AsyncClient, cigna_payer: Payer
) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": cigna_payer.id,
            "procedures": [{"code": "D0120", "description": "Eval", "amount": 50.00}],
            "total_amount": 50.00,
        },
    )
    assert response.status_code == 200


async def test_create_claim_with_nonexistent_payer_is_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": 999999,
            "procedures": [{"code": "D0120", "description": "Eval", "amount": 50.00}],
            "total_amount": 50.00,
        },
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["validation_errors"]
    assert any("999999" in e for e in errors)
