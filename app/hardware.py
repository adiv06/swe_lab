"""Errors shared by hardware-unit operations."""


class HardwareError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(HardwareError):
    status_code = 404


class ConflictError(HardwareError):
    status_code = 409
