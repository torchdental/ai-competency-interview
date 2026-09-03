from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.claim import Claim, ClaimStatus
from src.models.procedure import Procedure

TERMINAL_STATUSES = (ClaimStatus.ACCEPTED, ClaimStatus.REJECTED)


class ProcedureNotFoundError(Exception):
    pass


class ClaimSettledError(Exception):
    """Raised when a procedure's claim is financially settled and can no longer change"""

    def __init__(self, status: ClaimStatus) -> None:
        super().__init__(f"Claim is {status.value} and can no longer be modified")
        self.status = status


class ProcedureService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def set_voided(self, procedure_id: int, practice_id: str, voided: bool) -> Claim:
        """Void or restore a procedure and return its claim with the total recomputed"""
        result = await self.session.execute(
            select(Procedure)
            .where(Procedure.id == procedure_id)
            .options(selectinload(Procedure.claim).selectinload(Claim.procedures))
        )
        procedure = result.scalar_one_or_none()
        # A procedure is only reachable through its claim, so an unowned claim reads as missing.
        if procedure is None or procedure.claim.practice_id != practice_id:
            raise ProcedureNotFoundError

        claim = procedure.claim
        if claim.status in TERMINAL_STATUSES:
            raise ClaimSettledError(claim.status)

        procedure.voided = voided
        claim.total_amount = sum(p.amount for p in claim.procedures if not p.voided)
        await self.session.commit()

        # The commit expires Claim.updated_at via its onupdate, so re-load rather than
        # leave the caller to trigger a lazy refresh outside the async context.
        reloaded = await self.session.execute(
            select(Claim).where(Claim.id == claim.id).options(selectinload(Claim.procedures))
        )
        return reloaded.scalar_one()
