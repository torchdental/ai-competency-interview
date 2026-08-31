class ClaimNotFoundError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    def __init__(self, current: str, requested: str):
        super().__init__(f"Cannot transition from {current!r} to {requested!r}")
        self.current = current
        self.requested = requested


class ClaimValidationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__(f"Validation failed: {errors}")
        self.errors = errors
