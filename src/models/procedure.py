from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Procedure(Base):
    __tablename__ = "procedures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    voided: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    claim: Mapped["Claim"] = relationship("Claim", back_populates="procedures")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "code": self.code,
            "description": self.description,
            "amount": self.amount,
            "voided": self.voided,
        }
