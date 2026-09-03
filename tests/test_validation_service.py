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


def test_validate_claim_unrecognized_code(validation_service: ValidationService) -> None:
    errors = validation_service.validate_claim([
        {"code": "D9999", "amount": 50.00},
    ])
    assert len(errors) == 1
    assert "D9999" in errors[0]
    assert "unrecognized" in errors[0]


def test_unrecognized_code_does_not_mask_other_errors(
    validation_service: ValidationService,
) -> None:
    errors = validation_service.validate_claim([
        {"code": "D9999", "amount": 50.00},
        {"code": "D0120", "amount": 200.00},
    ])
    assert len(errors) == 2


@pytest.mark.parametrize(
    ("code", "max_amount"),
    [
        ("D1110", 110.00),
        ("D1120", 85.00),
        ("D2140", 165.00),
        ("D2150", 205.00),
    ],
)
def test_new_codes_allow_amount_up_to_max(
    validation_service: ValidationService, code: str, max_amount: float
) -> None:
    assert validation_service.validate_claim([{"code": code, "amount": max_amount}]) == []


@pytest.mark.parametrize(
    ("code", "max_amount"),
    [
        ("D1110", 110.00),
        ("D1120", 85.00),
        ("D2140", 165.00),
        ("D2150", 205.00),
    ],
)
def test_new_codes_reject_amount_over_max(
    validation_service: ValidationService, code: str, max_amount: float
) -> None:
    errors = validation_service.validate_claim([{"code": code, "amount": max_amount + 0.01}])
    assert len(errors) == 1
    assert code in errors[0]
    assert "exceeds maximum" in errors[0]


def test_unrestricted_code_valid_for_any_payer(validation_service: ValidationService) -> None:
    for payer_code in ("DD001", "CIG001", "AET001"):
        assert (
            validation_service.validate_claim(
                [{"code": "D0120", "amount": 50.00}], payer_code=payer_code
            )
            == []
        )


def test_unrestricted_code_valid_without_payer_code(
    validation_service: ValidationService,
) -> None:
    assert validation_service.validate_claim([{"code": "D0120", "amount": 50.00}]) == []


@pytest.mark.parametrize(
    ("code", "amount", "payer_code"),
    [
        ("D3310", 750.00, "DD001"),
        ("D3330", 1100.00, "CIG001"),
    ],
)
def test_restricted_code_valid_for_its_payer(
    validation_service: ValidationService, code: str, amount: float, payer_code: str
) -> None:
    assert validation_service.validate_claim([{"code": code, "amount": amount}], payer_code=payer_code) == []


@pytest.mark.parametrize(
    ("code", "amount", "payer_code"),
    [
        ("D3310", 750.00, "CIG001"),
        ("D3330", 1100.00, "DD001"),
    ],
)
def test_restricted_code_rejected_for_other_payer(
    validation_service: ValidationService, code: str, amount: float, payer_code: str
) -> None:
    errors = validation_service.validate_claim([{"code": code, "amount": amount}], payer_code=payer_code)
    assert len(errors) == 1
    assert code in errors[0]
    assert payer_code in errors[0]


def test_restricted_code_skips_payer_check_without_payer_code(
    validation_service: ValidationService,
) -> None:
    assert validation_service.validate_claim([{"code": "D3310", "amount": 750.00}]) == []
