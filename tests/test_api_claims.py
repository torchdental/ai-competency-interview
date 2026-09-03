from httpx import AsyncClient
from src.models.claim import ClaimStatus
from src.models.payer import Payer
from src.services.claim_service import ClaimService


async def _claim_in_status(
    claim_service: ClaimService,
    payer: Payer,
    status: ClaimStatus,
    practice_id: str = "practice-1",
    patient_name: str = "Alice",
):
    claim = await claim_service.create_claim(
        practice_id=practice_id,
        patient_name=patient_name,
        payer_id=payer.id,
        procedures=[{"code": "D0120", "description": "Eval", "amount": 50.00}],
        total_amount=50.00,
    )
    if status is not ClaimStatus.PENDING:
        claim.status = status
        await claim_service.session.commit()
    return claim


async def test_validated_claim_returns_to_pending(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await _claim_in_status(claim_service, payer, ClaimStatus.VALIDATED)

    response = await client.patch(
        f"/api/claims/{claim.id}/status",
        params={"practice_id": "practice-1"},
        json={"status": "pending"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert len(body["procedures"]) == 1


async def test_pending_claim_can_be_rejected(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await _claim_in_status(claim_service, payer, ClaimStatus.PENDING)

    response = await client.patch(
        f"/api/claims/{claim.id}/status",
        params={"practice_id": "practice-1"},
        json={"status": "rejected"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


async def test_accepted_claim_cannot_return_to_pending(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await _claim_in_status(claim_service, payer, ClaimStatus.ACCEPTED)

    response = await client.patch(
        f"/api/claims/{claim.id}/status",
        params={"practice_id": "practice-1"},
        json={"status": "pending"},
    )
    assert response.status_code == 400


async def test_rejected_claim_cannot_return_to_pending(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await _claim_in_status(claim_service, payer, ClaimStatus.REJECTED)

    response = await client.patch(
        f"/api/claims/{claim.id}/status",
        params={"practice_id": "practice-1"},
        json={"status": "pending"},
    )
    assert response.status_code == 400


async def test_pending_claim_cannot_skip_to_accepted(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await _claim_in_status(claim_service, payer, ClaimStatus.PENDING)

    response = await client.patch(
        f"/api/claims/{claim.id}/status",
        params={"practice_id": "practice-1"},
        json={"status": "accepted"},
    )
    assert response.status_code == 400
    assert "pending" in response.json()["detail"]
