from httpx import AsyncClient
from src.models.payer import Payer
from src.services.claim_service import ClaimService


async def test_create_claim_returns_pending(client: AsyncClient, payer: Payer) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": payer.id,
            "procedures": [{"code": "D0120", "description": "Eval", "amount": 50.00}],
            "total_amount": 50.00,
        },
    )
    assert response.status_code == 200
    claim = response.json()["claim"]
    assert claim["status"] == "pending"
    assert len(claim["procedures"]) == 1


async def test_create_claim_unrecognized_code_is_422(client: AsyncClient, payer: Payer) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": payer.id,
            "procedures": [{"code": "D9999", "description": "Bogus", "amount": 50.00}],
            "total_amount": 50.00,
        },
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["validation_errors"]
    assert any("D9999" in e for e in errors)


async def test_create_claim_over_max_amount_is_422(client: AsyncClient, payer: Payer) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": payer.id,
            "procedures": [{"code": "D0120", "description": "Eval", "amount": 500.00}],
            "total_amount": 500.00,
        },
    )
    assert response.status_code == 422


async def test_list_claims_is_scoped_to_practice(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Alice",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )
    await claim_service.create_claim(
        practice_id="practice-2",
        patient_name="Bob",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )

    response = await client.get("/api/claims", params={"practice_id": "practice-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["claims"][0]["patient_name"] == "Alice"


async def test_get_claim_from_other_practice_is_404(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Alice",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )
    response = await client.get(
        f"/api/claims/{claim.id}", params={"practice_id": "practice-2"}
    )
    assert response.status_code == 404


async def test_delete_claim_from_other_practice_is_403(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Alice",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )
    response = await client.delete(
        f"/api/claims/{claim.id}", params={"practice_id": "practice-2"}
    )
    assert response.status_code == 403
