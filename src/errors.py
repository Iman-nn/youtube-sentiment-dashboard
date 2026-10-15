"""Safe application exceptions.

Only ``user_message`` is rendered in the browser. Internal exception context is
kept in server logs so file paths and parser details are not exposed publicly.
"""


class DashboardError(Exception):
    def __init__(self, user_message: str, internal_message: str = "") -> None:
        super().__init__(internal_message or user_message)
        self.user_message = user_message


class DataSourceError(DashboardError):
    """The configured data source cannot be safely opened."""


class DataValidationError(DashboardError):
    """The CSV structure cannot produce trustworthy analytics."""
