class ErrorEvent(Exception):
    """Raised when log level is ERROR. Sending message to Telegram."""

    pass


class EndpointError(ErrorEvent):
    """Raised when endpoint is not available."""

    pass


class ErrorEventNotForSending(Exception):
    """Raised when log level is ERROR. Not sending message to Telegram."""

    pass


class MessageError(ErrorEventNotForSending):
    """Raised when problem with sending message occurs."""

    pass


class DateError(ErrorEventNotForSending):
    """Raised when current_date not in response."""

    pass
