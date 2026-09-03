import json

from src.common.constants import PROCEDURE_CODES_PATH


class ValidationService:
    def __init__(self) -> None:
        with open(PROCEDURE_CODES_PATH) as f:
            self._codes: dict = json.load(f)

    def validate_procedure_code(self, code: str) -> dict | None:
        """Return the reference entry for a code, or None if it is not in the allowed set"""
        return self._codes.get(code)

    def validate_claim(self, procedures: list[dict]) -> list[str]:
        errors = []
        for proc in procedures:
            code_info = self.validate_procedure_code(proc["code"])
            if code_info is None:
                errors.append(f"Procedure {proc['code']}: unrecognized code")
                continue
            if proc["amount"] > code_info["max_amount"]:
                errors.append(
                    f"Procedure {proc['code']}: amount ${proc['amount']:.2f} "
                    f"exceeds maximum ${code_info['max_amount']:.2f}"
                )
        return errors
