from datetime import datetime

from httpx import AsyncClient
from src.models.claim import ClaimStatus
from src.models.payer import Payer
from src.services.claim_service import ClaimService


def _timestamp(iso: str) -> datetime:
    """Parse a naive UTC timestamp, matching how the database stores created_at"""
    return datetime.fromisoformat(iso)


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


async def _claim_created_at(
    claim_service: ClaimService,
    payer: Payer,
    created_at: datetime,
    practice_id: str = "practice-1",
):
    claim = await _claim_in_status(
        claim_service, payer, ClaimStatus.PENDING, practice_id=practice_id
    )
    claim.created_at = created_at
    await claim_service.session.commit()
    return claim


async def test_list_claims_without_filters_returns_all(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    await _claim_in_status(claim_service, payer, ClaimStatus.PENDING)
    await _claim_in_status(claim_service, payer, ClaimStatus.VALIDATED)

    response = await client.get("/api/claims", params={"practice_id": "practice-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["claims"]) == 2


async def test_list_claims_filtered_by_status(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    await _claim_in_status(claim_service, payer, ClaimStatus.PENDING)
    await _claim_in_status(claim_service, payer, ClaimStatus.VALIDATED)
    await _claim_in_status(claim_service, payer, ClaimStatus.ACCEPTED)
    await _claim_in_status(claim_service, payer, ClaimStatus.REJECTED)

    for status in ClaimStatus:
        response = await client.get(
            "/api/claims", params={"practice_id": "practice-1", "status": status.value}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert [c["status"] for c in body["claims"]] == [status.value]


async def test_status_filter_does_not_leak_other_practices(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    await _claim_in_status(
        claim_service, payer, ClaimStatus.VALIDATED, practice_id="practice-1", patient_name="Alice"
    )
    await _claim_in_status(
        claim_service, payer, ClaimStatus.VALIDATED, practice_id="practice-2", patient_name="Bob"
    )

    response = await client.get(
        "/api/claims", params={"practice_id": "practice-1", "status": "validated"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["claims"][0]["patient_name"] == "Alice"


async def test_unknown_status_value_is_422(client: AsyncClient) -> None:
    response = await client.get(
        "/api/claims", params={"practice_id": "practice-1", "status": "garbage"}
    )
    assert response.status_code == 422


async def test_submitted_after_includes_the_boundary(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    boundary = _timestamp("2026-03-01T12:00:00")
    await _claim_created_at(claim_service, payer, _timestamp("2026-02-28T12:00:00"))
    await _claim_created_at(claim_service, payer, boundary)
    await _claim_created_at(claim_service, payer, _timestamp("2026-03-02T12:00:00"))

    response = await client.get(
        "/api/claims",
        params={"practice_id": "practice-1", "submitted_after": boundary.isoformat()},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_submitted_before_includes_the_boundary(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    boundary = _timestamp("2026-03-01T12:00:00")
    await _claim_created_at(claim_service, payer, _timestamp("2026-02-28T12:00:00"))
    await _claim_created_at(claim_service, payer, boundary)
    await _claim_created_at(claim_service, payer, _timestamp("2026-03-02T12:00:00"))

    response = await client.get(
        "/api/claims",
        params={"practice_id": "practice-1", "submitted_before": boundary.isoformat()},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_date_range_and_status_filters_combine(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    in_range = await _claim_created_at(claim_service, payer, _timestamp("2026-03-01T12:00:00"))
    in_range.status = ClaimStatus.VALIDATED
    out_of_range = await _claim_created_at(claim_service, payer, _timestamp("2026-04-01T12:00:00"))
    out_of_range.status = ClaimStatus.VALIDATED
    await claim_service.session.commit()
    await _claim_created_at(claim_service, payer, _timestamp("2026-03-02T12:00:00"))

    response = await client.get(
        "/api/claims",
        params={
            "practice_id": "practice-1",
            "status": "validated",
            "submitted_after": "2026-03-01T00:00:00",
            "submitted_before": "2026-03-31T23:59:59",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["claims"][0]["id"] == in_range.id


async def test_timezone_aware_bounds_are_compared_in_utc(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    await _claim_created_at(claim_service, payer, _timestamp("2026-03-01T12:00:00"))

    response = await client.get(
        "/api/claims",
        params={"practice_id": "practice-1", "submitted_after": "2026-03-01T14:00:00+05:00"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
