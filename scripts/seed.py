"""Seed the database with payers and sample claims."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.db import AsyncSessionLocal, init_db
from src.models.claim import Claim, ClaimStatus
from src.models.payer import Payer
from src.models.procedure import Procedure


PAYERS = [
    {"name": "Delta Dental", "payer_code": "DD001"},
    {"name": "Cigna", "payer_code": "CIG001"},
    {"name": "Aetna", "payer_code": "AET001"},
]

PRACTICE_ID = "practice-1"


async def seed() -> None:
    await init_db()

    async with AsyncSessionLocal() as session:
        payers = []
        for p in PAYERS:
            payer = Payer(**p)
            session.add(payer)
            payers.append(payer)
        await session.flush()

        claims_data = [
            {
                "patient_name": "Alice Johnson",
                "payer": payers[0],
                "status": ClaimStatus.PENDING,
                "procedures": [
                    {"code": "D0120", "description": "Periodic oral evaluation", "amount": 65.00},
                    {"code": "D0210", "description": "Complete series of radiographic images", "amount": 150.00},
                ],
            },
            {
                "patient_name": "Bob Martinez",
                "payer": payers[1],
                "status": ClaimStatus.VALIDATED,
                "procedures": [
                    {"code": "D0140", "description": "Limited oral evaluation", "amount": 85.00},
                    {"code": "D7140", "description": "Extraction, erupted tooth or exposed root", "amount": 185.00},
                ],
            },
            {
                "patient_name": "Carol Lee",
                "payer": payers[2],
                "status": ClaimStatus.ACCEPTED,
                "procedures": [
                    {"code": "D2330", "description": "Resin-based composite, one surface, anterior", "amount": 180.00},
                ],
            },
            {
                "patient_name": "David Kim",
                "payer": payers[0],
                "status": ClaimStatus.REJECTED,
                "procedures": [
                    {"code": "D7210", "description": "Surgical extraction of erupted tooth", "amount": 340.00},
                ],
            },
            {
                "patient_name": "Emma Davis",
                "payer": payers[1],
                "status": ClaimStatus.PENDING,
                "procedures": [
                    {"code": "D0120", "description": "Periodic oral evaluation", "amount": 70.00},
                    {"code": "D0140", "description": "Limited oral evaluation", "amount": 90.00},
                ],
            },
        ]

        for cd in claims_data:
            procedures = [Procedure(**p) for p in cd["procedures"]]
            total = sum(p.amount for p in procedures)
            claim = Claim(
                practice_id=PRACTICE_ID,
                patient_name=cd["patient_name"],
                payer_id=cd["payer"].id,
                status=cd["status"],
                total_amount=total,
                procedures=procedures,
            )
            session.add(claim)

        await session.commit()
        print("Database seeded successfully.")
        print(f"  Payers: {len(PAYERS)}")
        print(f"  Claims: {len(claims_data)}")


if __name__ == "__main__":
    asyncio.run(seed())
