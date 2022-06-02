class ErrorEvent(Exception):
    """Raised when log level is ERROR."""

    pass


class ConnectionError(ErrorEvent):
    """Raised when HTTP status is not 200."""

    pass


class EndpointError(ErrorEvent):
    """Raised when endpoint is not available."""

    pass
