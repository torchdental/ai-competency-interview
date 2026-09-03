from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.db import get_session
from src.services.procedure_service import (
    ClaimSettledError,
    ProcedureNotFoundError,
    ProcedureService,
)

router = APIRouter(prefix="/api")


def get_procedure_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProcedureService:
    return ProcedureService(session)


ProcedureServiceDep = Annotated[ProcedureService, Depends(get_procedure_service)]


class ProcedureVoidRequest(BaseModel):
    voided: bool


async def _set_voided(
    service: ProcedureService, procedure_id: int, practice_id: str, voided: bool
) -> dict:
    try:
        claim = await service.set_voided(procedure_id, practice_id, voided)
    except ProcedureNotFoundError:
        raise HTTPException(status_code=404, detail="Not found") from None
    except ClaimSettledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return claim.to_dict()


@router.patch("/procedures/{procedure_id}")
async def void_procedure(
    procedure_id: int,
    practice_id: str,
    data: ProcedureVoidRequest,
    service: ProcedureServiceDep,
):
    return await _set_voided(service, procedure_id, practice_id, data.voided)


@router.post("/procedures/{procedure_id}/restore")
async def restore_procedure(
    procedure_id: int,
    practice_id: str,
    service: ProcedureServiceDep,
):
    return await _set_voided(service, procedure_id, practice_id, False)
