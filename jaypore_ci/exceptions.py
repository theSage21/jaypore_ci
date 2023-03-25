class BadConfig(Exception):
    """
    Raised when a given configuration for a pipeline will cause errors /
    unexpected behaviour if it is allowed to run.
    """
