from httpx import AsyncClient
from src.models.payer import Payer


async def test_create_claim_with_new_code(client: AsyncClient, payer: Payer) -> None:
    response = await client.post(
        "/api/claims",
        json={
            "practice_id": "practice-1",
            "patient_name": "John Doe",
            "payer_id": payer.id,
            "procedures": [{"code": "D1110", "description": "Prophy", "amount": 110.00}],
            "total_amount": 110.00,
        },
    )
    assert response.status_code == 200
