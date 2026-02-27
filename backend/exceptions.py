from fastapi import HTTPException, status

class AppError(Exception):
    def __init__(self, message: str, code: int = 400, error_type: str = "InternalError"):
        self.message = message
        self.code = code
        self.error_type = error_type
        super().__init__(self.message)

class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code=status.HTTP_401_UNAUTHORIZED, error_type="AuthenticationError")

class AuthorizationError(AppError):
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, code=status.HTTP_403_FORBIDDEN, error_type="AuthorizationError")

class ValidationError(AppError):
    def __init__(self, message: str = "Invalid input data"):
        super().__init__(message, code=status.HTTP_400_BAD_REQUEST, error_type="ValidationError")

class PaymentError(AppError):
    def __init__(self, message: str = "Payment processing failed"):
        super().__init__(message, code=status.HTTP_400_BAD_REQUEST, error_type="PaymentError")

class BusinessLogicError(AppError):
    def __init__(self, message: str):
        super().__init__(message, code=status.HTTP_400_BAD_REQUEST, error_type="BusinessLogicError")
