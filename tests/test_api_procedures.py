import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.claim import Claim, ClaimStatus
from src.models.payer import Payer
from src.services.claim_service import ClaimService

PRACTICE = "practice-1"
OTHER_PRACTICE = "practice-2"


async def make_claim(
    claim_service: ClaimService,
    payer: Payer,
    procedures: list[dict],
    practice_id: str = PRACTICE,
) -> Claim:
    return await claim_service.create_claim(
        practice_id=practice_id,
        patient_name="John Doe",
        payer_id=payer.id,
        procedures=procedures,
        total_amount=sum(p["amount"] for p in procedures),
    )


async def test_void_sets_flag_and_lowers_total(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service,
        payer,
        [
            {"code": "D0120", "description": "Eval", "amount": 50.00},
            {"code": "D0210", "description": "X-ray", "amount": 30.00},
        ],
    )
    target = claim.procedures[0]

    response = await client.patch(
        f"/api/procedures/{target.id}",
        params={"practice_id": PRACTICE},
        json={"voided": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_amount"] == pytest.approx(30.00)
    voided = next(p for p in body["procedures"] if p["id"] == target.id)
    assert voided["voided"] is True


async def test_voided_procedure_still_listed_on_claim(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service, payer, [{"code": "D0120", "description": "Eval", "amount": 50.00}]
    )
    target = claim.procedures[0]

    await client.patch(
        f"/api/procedures/{target.id}",
        params={"practice_id": PRACTICE},
        json={"voided": True},
    )
    response = await client.get(f"/api/claims/{claim.id}", params={"practice_id": PRACTICE})

    assert response.status_code == 200
    procedures = response.json()["procedures"]
    assert [p["id"] for p in procedures] == [target.id]
    assert procedures[0]["voided"] is True


async def test_restore_adds_amount_back(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service,
        payer,
        [
            {"code": "D0120", "description": "Eval", "amount": 50.00},
            {"code": "D0210", "description": "X-ray", "amount": 30.00},
        ],
    )
    target = claim.procedures[0]

    await client.patch(
        f"/api/procedures/{target.id}",
        params={"practice_id": PRACTICE},
        json={"voided": True},
    )
    response = await client.post(
        f"/api/procedures/{target.id}/restore", params={"practice_id": PRACTICE}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_amount"] == pytest.approx(80.00)
    assert all(p["voided"] is False for p in body["procedures"])


async def test_voiding_twice_is_idempotent(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service,
        payer,
        [
            {"code": "D0120", "description": "Eval", "amount": 50.00},
            {"code": "D0210", "description": "X-ray", "amount": 30.00},
        ],
    )
    target = claim.procedures[0]
    params = {"practice_id": PRACTICE}

    first = await client.patch(
        f"/api/procedures/{target.id}", params=params, json={"voided": True}
    )
    second = await client.patch(
        f"/api/procedures/{target.id}", params=params, json={"voided": True}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["total_amount"] == pytest.approx(30.00)


async def test_restoring_unvoided_procedure_is_idempotent(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service, payer, [{"code": "D0120", "description": "Eval", "amount": 50.00}]
    )
    target = claim.procedures[0]

    response = await client.post(
        f"/api/procedures/{target.id}/restore", params={"practice_id": PRACTICE}
    )

    assert response.status_code == 200
    assert response.json()["total_amount"] == pytest.approx(50.00)


async def test_voiding_every_procedure_zeroes_the_total(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service,
        payer,
        [
            {"code": "D0120", "description": "Eval", "amount": 50.00},
            {"code": "D0210", "description": "X-ray", "amount": 30.00},
        ],
    )
    params = {"practice_id": PRACTICE}

    for procedure in claim.procedures:
        response = await client.patch(
            f"/api/procedures/{procedure.id}", params=params, json={"voided": True}
        )
        assert response.status_code == 200

    assert response.json()["total_amount"] == pytest.approx(0.00)


async def test_void_across_practices_is_404_and_leaves_procedure_intact(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service, payer, [{"code": "D0120", "description": "Eval", "amount": 50.00}]
    )
    target = claim.procedures[0]

    response = await client.patch(
        f"/api/procedures/{target.id}",
        params={"practice_id": OTHER_PRACTICE},
        json={"voided": True},
    )

    assert response.status_code == 404
    owner_view = await client.get(f"/api/claims/{claim.id}", params={"practice_id": PRACTICE})
    assert owner_view.json()["procedures"][0]["voided"] is False
    assert owner_view.json()["total_amount"] == pytest.approx(50.00)


async def test_restore_across_practices_is_404(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service, payer, [{"code": "D0120", "description": "Eval", "amount": 50.00}]
    )

    response = await client.post(
        f"/api/procedures/{claim.procedures[0].id}/restore",
        params={"practice_id": OTHER_PRACTICE},
    )

    assert response.status_code == 404


async def test_void_nonexistent_procedure_is_404(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/procedures/9999", params={"practice_id": PRACTICE}, json={"voided": True}
    )
    assert response.status_code == 404


async def test_restore_nonexistent_procedure_is_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/procedures/9999/restore", params={"practice_id": PRACTICE}
    )
    assert response.status_code == 404


@pytest.mark.parametrize("status", [ClaimStatus.ACCEPTED, ClaimStatus.REJECTED])
async def test_void_on_terminal_claim_is_409(
    client: AsyncClient,
    session: AsyncSession,
    claim_service: ClaimService,
    payer: Payer,
    status: ClaimStatus,
) -> None:
    claim = await make_claim(
        claim_service, payer, [{"code": "D0120", "description": "Eval", "amount": 50.00}]
    )
    claim.status = status
    await session.commit()

    response = await client.patch(
        f"/api/procedures/{claim.procedures[0].id}",
        params={"practice_id": PRACTICE},
        json={"voided": True},
    )

    assert response.status_code == 409
    assert claim.total_amount == pytest.approx(50.00)


@pytest.mark.parametrize("status", [ClaimStatus.ACCEPTED, ClaimStatus.REJECTED])
async def test_restore_on_terminal_claim_is_409(
    client: AsyncClient,
    session: AsyncSession,
    claim_service: ClaimService,
    payer: Payer,
    status: ClaimStatus,
) -> None:
    claim = await make_claim(
        claim_service, payer, [{"code": "D0120", "description": "Eval", "amount": 50.00}]
    )
    claim.status = status
    await session.commit()

    response = await client.post(
        f"/api/procedures/{claim.procedures[0].id}/restore",
        params={"practice_id": PRACTICE},
    )

    assert response.status_code == 409


async def test_patch_voided_false_restores(
    client: AsyncClient, claim_service: ClaimService, payer: Payer
) -> None:
    claim = await make_claim(
        claim_service, payer, [{"code": "D0120", "description": "Eval", "amount": 50.00}]
    )
    target = claim.procedures[0]
    params = {"practice_id": PRACTICE}

    await client.patch(f"/api/procedures/{target.id}", params=params, json={"voided": True})
    response = await client.patch(
        f"/api/procedures/{target.id}", params=params, json={"voided": False}
    )

    assert response.status_code == 200
    assert response.json()["total_amount"] == pytest.approx(50.00)
    assert response.json()["procedures"][0]["voided"] is False
