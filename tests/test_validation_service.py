import pytest

from src.services.validation_service import ValidationService


@pytest.fixture
def validation_service() -> ValidationService:
    return ValidationService()


def test_valid_procedure_code(validation_service: ValidationService) -> None:
    result = validation_service.validate_procedure_code("D0120")
    assert result["description"] == "Periodic oral evaluation"
    assert result["max_amount"] == 75.00


def test_validate_claim_within_limits(validation_service: ValidationService) -> None:
    errors = validation_service.validate_claim([
        {"code": "D0120", "amount": 50.00},
        {"code": "D0140", "amount": 80.00},
    ])
    assert errors == []


def test_validate_claim_exceeds_max_amount(validation_service: ValidationService) -> None:
    errors = validation_service.validate_claim([
        {"code": "D0120", "amount": 200.00},
    ])
    assert len(errors) == 1
    assert "D0120" in errors[0]
    assert "exceeds maximum" in errors[0]


def test_validate_claim_multiple_procedures(validation_service: ValidationService) -> None:
    errors = validation_service.validate_claim([
        {"code": "D0120", "amount": 50.00},
        {"code": "D7210", "amount": 400.00},  # max is 350.00
    ])
    assert len(errors) == 1
    assert "D7210" in errors[0]
