import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.exceptions import ClaimNotEditableError
from src.models.claim import Claim, ClaimStatus
from src.models.payer import Payer
from src.models.procedure import Procedure
from src.services.claim_service import ClaimService


async def create_claim(
    claim_service: ClaimService, payer: Payer, total_amount: float = 215.00
) -> Claim:
    return await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Jane Doe",
        payer_id=payer.id,
        procedures=[
            {"code": "D0120", "amount": 65.00},
            {"code": "D0210", "amount": 150.00},
        ],
        total_amount=total_amount,
    )


def procedure_by_code(claim: Claim, code: str) -> Procedure:
    return next(p for p in claim.procedures if p.code == code)


async def test_new_procedures_are_not_voided(claim_service: ClaimService, payer: Payer) -> None:
    claim = await create_claim(claim_service, payer)
    assert [p.voided for p in claim.procedures] == [False, False]
    assert all(p.to_dict()["voided"] is False for p in claim.procedures)


async def test_void_procedure_keeps_it_on_the_claim(
    claim_service: ClaimService, payer: Payer
) -> None:
    claim = await create_claim(claim_service, payer)
    kept = procedure_by_code(claim, "D0120")
    target = procedure_by_code(claim, "D0210")
    procedure = await claim_service.get_procedure(target.id, "practice-1")

    updated = await claim_service.set_procedure_voided(procedure, True)

    assert updated.id == claim.id
    assert {p.id: p.voided for p in updated.procedures} == {kept.id: False, target.id: True}


async def test_void_procedure_excludes_it_from_claim_total(
    claim_service: ClaimService, payer: Payer
) -> None:
    claim = await create_claim(claim_service, payer)
    target = procedure_by_code(claim, "D0210")
    procedure = await claim_service.get_procedure(target.id, "practice-1")

    updated = await claim_service.set_procedure_voided(procedure, True)

    assert updated.total_amount == 65.00


async def test_void_procedure_recomputes_total_from_active_procedures(
    claim_service: ClaimService, payer: Payer
) -> None:
    claim = await create_claim(claim_service, payer, total_amount=999.00)
    target = procedure_by_code(claim, "D0210")
    procedure = await claim_service.get_procedure(target.id, "practice-1")

    updated = await claim_service.set_procedure_voided(procedure, True)

    assert updated.total_amount == 65.00


async def test_voiding_an_already_voided_procedure_is_a_no_op(
    claim_service: ClaimService, payer: Payer
) -> None:
    claim = await create_claim(claim_service, payer)
    target = procedure_by_code(claim, "D0210")
    procedure = await claim_service.get_procedure(target.id, "practice-1")
    await claim_service.set_procedure_voided(procedure, True)

    updated = await claim_service.set_procedure_voided(procedure, True)

    assert procedure_by_code(updated, "D0210").voided is True
    assert updated.total_amount == 65.00


async def test_can_void_procedure_on_validated_claim(
    claim_service: ClaimService, session: AsyncSession, payer: Payer
) -> None:
    claim = await create_claim(claim_service, payer)
    claim.status = ClaimStatus.VALIDATED
    await session.commit()
    target = procedure_by_code(claim, "D0210")
    procedure = await claim_service.get_procedure(target.id, "practice-1")

    updated = await claim_service.set_procedure_voided(procedure, True)

    assert updated.status == ClaimStatus.VALIDATED
    assert updated.total_amount == 65.00


@pytest.mark.parametrize("status", [ClaimStatus.ACCEPTED, ClaimStatus.REJECTED])
async def test_cannot_void_procedure_on_terminal_claim(
    claim_service: ClaimService, session: AsyncSession, payer: Payer, status: ClaimStatus
) -> None:
    claim = await create_claim(claim_service, payer)
    claim.status = status
    await session.commit()
    target = procedure_by_code(claim, "D0210")
    procedure = await claim_service.get_procedure(target.id, "practice-1")

    with pytest.raises(ClaimNotEditableError):
        await claim_service.set_procedure_voided(procedure, True)

    assert procedure.voided is False
    assert claim.total_amount == 215.00


async def test_get_procedure_is_scoped_to_practice(
    claim_service: ClaimService, payer: Payer
) -> None:
    claim = await create_claim(claim_service, payer)
    procedure_id = claim.procedures[0].id

    assert await claim_service.get_procedure(procedure_id, "practice-2") is None
    assert await claim_service.get_procedure(procedure_id, "practice-1") is not None
