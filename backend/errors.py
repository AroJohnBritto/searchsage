class ConfigError(Exception):
    """Raised when a tier is missing required configuration, such as an API key.

    Config errors are never retried, since retrying will not fix a missing
    credential. The orchestrator should catch this and move on to the next
    tier immediately.
    """


class ProviderError(Exception):
    """Raised when a tier's upstream call fails in a way that might succeed
    on a later attempt, such as a network error, timeout, or a 5xx response.

    Provider errors are retried with backoff before the orchestrator falls
    through to the next tier.
    """
