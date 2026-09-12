from typing import Any

from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required", code: str = "UNAUTHORIZED"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, code=code, message=message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Permission denied", code: str = "FORBIDDEN"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, code=code, message=message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, code=code, message=message)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, code=code, message=message)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", code: str = "BAD_REQUEST", details: Any | None = None):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, code=code, message=message, details=details)
