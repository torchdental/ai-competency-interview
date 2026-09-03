import pytest
from src.common.exceptions import InvalidStatusTransitionError
from src.models.claim import ClaimStatus
from src.models.payer import Payer
from src.services.claim_service import ClaimService


async def test_create_claim(claim_service: ClaimService, payer: Payer) -> None:
    claim = await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="John Doe",
        payer_id=payer.id,
        procedures=[{"code": "D0120", "amount": 50.00}],
        total_amount=50.00,
    )
    assert claim.id is not None
    assert claim.status == ClaimStatus.PENDING
    assert len(claim.procedures) == 1


async def test_get_claims_scoped_to_practice(claim_service: ClaimService, payer: Payer) -> None:
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
    claims = await claim_service.get_claims("practice-1")
    assert len(claims) == 1
    assert claims[0].patient_name == "Alice"


async def test_valid_status_transition(claim_service: ClaimService, payer: Payer) -> None:
    claim = await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Jane Doe",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )
    updated = await claim_service.transition_status(claim, ClaimStatus.VALIDATED)
    assert updated.status == ClaimStatus.VALIDATED


async def test_invalid_status_transition_raises(claim_service: ClaimService, payer: Payer) -> None:
    claim = await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Jane Doe",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )
    with pytest.raises(InvalidStatusTransitionError):
        await claim_service.transition_status(claim, ClaimStatus.ACCEPTED)


async def test_get_claim_returns_none_for_wrong_practice(
    claim_service: ClaimService, payer: Payer
) -> None:
    claim = await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Alice",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )
    result = await claim_service.get_claim(claim.id, "practice-2")
    assert result is None


async def test_validated_claim_returns_to_pending(
    claim_service: ClaimService, payer: Payer
) -> None:
    claim = await claim_service.create_claim(
        practice_id="practice-1",
        patient_name="Jane Doe",
        payer_id=payer.id,
        procedures=[],
        total_amount=0.00,
    )
    validated = await claim_service.transition_status(claim, ClaimStatus.VALIDATED)
    returned = await claim_service.transition_status(validated, ClaimStatus.PENDING)
    assert returned.status == ClaimStatus.PENDING


async def test_terminal_states_allow_no_transitions(
    claim_service: ClaimService, payer: Payer
) -> None:
    for terminal in (ClaimStatus.ACCEPTED, ClaimStatus.REJECTED):
        claim = await claim_service.create_claim(
            practice_id="practice-1",
            patient_name="Jane Doe",
            payer_id=payer.id,
            procedures=[],
            total_amount=0.00,
        )
        claim.status = terminal
        await claim_service.session.commit()
        with pytest.raises(InvalidStatusTransitionError):
            await claim_service.transition_status(claim, ClaimStatus.PENDING)
