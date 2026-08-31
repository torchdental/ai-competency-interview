import json

from src.common.constants import PROCEDURE_CODES_PATH


class ValidationService:
    def __init__(self) -> None:
        with open(PROCEDURE_CODES_PATH) as f:
            self._codes: dict = json.load(f)

    def validate_procedure_code(self, code: str) -> dict:
        # Codes are not payer-specific — all payers share the same allowed set.
        # Feature gap: should accept payer_id and validate against payer-specific codes.
        return self._codes[code]

    def validate_claim(self, procedures: list[dict]) -> list[str]:
        errors = []
        for proc in procedures:
            code_info = self.validate_procedure_code(proc["code"])
            if proc["amount"] > code_info["max_amount"]:
                errors.append(
                    f"Procedure {proc['code']}: amount ${proc['amount']:.2f} "
                    f"exceeds maximum ${code_info['max_amount']:.2f}"
                )
        return errors
