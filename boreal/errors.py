"""Stable user-facing failure categories shared by IPC and UI."""
class BorealError(RuntimeError):
    def __init__(self, message, code="operation", component="service", retryable=False):
        super().__init__(message)
        self.code, self.component, self.retryable = code, component, retryable

    def payload(self):
        return dict(code=self.code, component=self.component, message=str(self), retryable=self.retryable)


def error_payload(exc):
    if isinstance(exc, BorealError):
        return exc.payload()
    code = "input" if isinstance(exc, (ValueError, KeyError, TypeError)) else (
        "permission" if isinstance(exc, PermissionError) else "operation")
    return dict(code=code, component="service", message=str(exc), retryable=False)
