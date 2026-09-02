from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Payer(Base):
    __tablename__ = "payers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    payer_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    claims: Mapped[list["Claim"]] = relationship("Claim", back_populates="payer")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "payer_code": self.payer_code,
        }
