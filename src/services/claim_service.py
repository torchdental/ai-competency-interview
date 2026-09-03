from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.exceptions import InvalidStatusTransitionError
from src.models.claim import Claim, ClaimStatus
from src.models.procedure import Procedure

VALID_TRANSITIONS: dict[ClaimStatus, list[ClaimStatus]] = {
    ClaimStatus.PENDING: [ClaimStatus.VALIDATED, ClaimStatus.REJECTED],
    ClaimStatus.VALIDATED: [ClaimStatus.ACCEPTED, ClaimStatus.REJECTED, ClaimStatus.PENDING],
    ClaimStatus.REJECTED: [],
    ClaimStatus.ACCEPTED: [],
}


class ClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_claims(self, practice_id: str) -> list[Claim]:
        result = await self.session.execute(
            select(Claim)
            .where(Claim.practice_id == practice_id)
            .options(selectinload(Claim.procedures))
            .order_by(Claim.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_claim(self, claim_id: int, practice_id: str) -> Claim | None:
        result = await self.session.execute(
            select(Claim)
            .where(Claim.id == claim_id, Claim.practice_id == practice_id)
            .options(selectinload(Claim.procedures))
        )
        return result.scalar_one_or_none()

    async def get_claim_unrestricted(self, claim_id: int) -> Claim | None:
        """Fetch a claim by ID without practice scoping. Used internally for authorization checks."""
        result = await self.session.execute(
            select(Claim).where(Claim.id == claim_id)
        )
        return result.scalar_one_or_none()

    async def create_claim(
        self,
        practice_id: str,
        patient_name: str,
        payer_id: int,
        procedures: list[dict],
        total_amount: float,
    ) -> Claim:
        claim = Claim(
            practice_id=practice_id,
            patient_name=patient_name,
            payer_id=payer_id,
            total_amount=total_amount,
        )
        self.session.add(claim)
        await self.session.flush()

        for proc in procedures:
            self.session.add(
                Procedure(
                    claim_id=claim.id,
                    code=proc["code"],
                    description=proc.get("description", ""),
                    amount=proc["amount"],
                )
            )

        await self.session.commit()

        result = await self.session.execute(
            select(Claim)
            .where(Claim.id == claim.id)
            .options(selectinload(Claim.procedures))
        )
        return result.scalar_one()

    async def transition_status(self, claim: Claim, new_status: ClaimStatus) -> Claim:
        allowed = VALID_TRANSITIONS.get(claim.status, [])
        if new_status not in allowed:
            raise InvalidStatusTransitionError(claim.status.value, new_status.value)
        claim.status = new_status
        await self.session.commit()

        # Re-select rather than refresh: the commit expires the instance, and callers
        # serialize the procedures, which cannot be lazy-loaded from async code.
        result = await self.session.execute(
            select(Claim)
            .where(Claim.id == claim.id)
            .options(selectinload(Claim.procedures))
        )
        return result.scalar_one()

    async def delete_claim(self, claim: Claim) -> None:
        await self.session.delete(claim)
        await self.session.commit()
