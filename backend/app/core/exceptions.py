"""
Custom exception classes for the application.

Each exception maps to a specific error scenario with
an appropriate HTTP status code and user-facing message.
"""


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OllamaConnectionError(AppException):
    """Raised when Ollama service is unreachable."""

    def __init__(self, message: str = "Ollama service is not reachable. Please ensure Ollama is running.") -> None:
        super().__init__(message=message, status_code=503)


class OllamaModelNotFoundError(AppException):
    """Raised when the requested model is not available in Ollama."""

    def __init__(self, model_name: str) -> None:
        message = f"Model '{model_name}' is not available in Ollama. Pull it with: ollama pull {model_name}"
        super().__init__(message=message, status_code=404)


class OllamaTimeoutError(AppException):
    """Raised when Ollama takes too long to respond."""

    def __init__(self, timeout: int) -> None:
        message = f"Ollama did not respond within {timeout} seconds. The model may be loading or the prompt may be too long."
        super().__init__(message=message, status_code=504)


class ChatSessionNotFoundError(AppException):
    """Raised when a chat session does not exist."""

    def __init__(self, session_id: str) -> None:
        message = f"Chat session '{session_id}' not found."
        super().__init__(message=message, status_code=404)
