from datetime import UTC, datetime

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


def _as_naive_utc(value: datetime) -> datetime:
    """Convert an aware datetime to naive UTC to match the stored timestamps

    created_at is written by the database without a timezone, and SQLAlchemy drops
    tzinfo on bind, so an offset-bearing bound would otherwise compare as wall clock.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


class ClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_claims(
        self,
        practice_id: str,
        *,
        status: ClaimStatus | None = None,
        submitted_after: datetime | None = None,
        submitted_before: datetime | None = None,
    ) -> list[Claim]:
        """List a practice's claims, optionally narrowed by status and creation date

        Both date bounds are inclusive.
        """
        query = select(Claim).where(Claim.practice_id == practice_id)
        if status is not None:
            query = query.where(Claim.status == status)
        if submitted_after is not None:
            query = query.where(Claim.created_at >= _as_naive_utc(submitted_after))
        if submitted_before is not None:
            query = query.where(Claim.created_at <= _as_naive_utc(submitted_before))

        result = await self.session.execute(
            query.options(selectinload(Claim.procedures)).order_by(Claim.created_at.desc())
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

        # Re-select rather than refresh: refresh leaves procedures unloaded, and callers
        # serialize them, which lazy-loading cannot do under async.
        result = await self.session.execute(
            select(Claim)
            .where(Claim.id == claim.id)
            .options(selectinload(Claim.procedures))
        )
        return result.scalar_one()

    async def delete_claim(self, claim: Claim) -> None:
        await self.session.delete(claim)
        await self.session.commit()
