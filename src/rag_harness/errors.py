class HarnessError(Exception):
    """Ordinary command or configuration error."""


class BlockedError(HarnessError):
    """The evaluation cannot be trusted or completed."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
