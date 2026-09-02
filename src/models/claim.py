from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class ClaimStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    practice_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    patient_name: Mapped[str] = mapped_column(String, nullable=False)
    payer_id: Mapped[int] = mapped_column(Integer, ForeignKey("payers.id"), nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(SAEnum(ClaimStatus), default=ClaimStatus.PENDING)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    payer: Mapped["Payer"] = relationship("Payer", back_populates="claims")
    procedures: Mapped[list["Procedure"]] = relationship(
        "Procedure", back_populates="claim", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "practice_id": self.practice_id,
            "patient_name": self.patient_name,
            "payer_id": self.payer_id,
            "status": self.status.value,
            "total_amount": self.total_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "procedures": [p.to_dict() for p in self.procedures],
        }
