"""
The basic logging module.
"""
import logging
from typing import Any

import structlog

# This is used to accumulate logs and is later sent over to the CI status as a
# separate log list
jaypore_logs = []


class JayporeLogger:
    """
    This is mainly used to collect logs into a single global variable so that
    the logs of the CI runner itself can also be posted as part of the CI
    report.
    """

    def __getstate__(self) -> str:
        return "stdout"

    def __setstate__(self, state: Any) -> None:
        pass

    def __deepcopy__(self, memodict: dict[Any, Any] = None) -> "JayporeLogger":
        return self.__class__()

    def msg(self, message: str) -> None:
        global jaypore_logs  # pylint: disable=global-statement
        jaypore_logs.append(message)
        if len(jaypore_logs) > 1500:
            jaypore_logs = jaypore_logs[-1000:]
        print(message)

    log = debug = info = warn = warning = msg
    fatal = failure = err = error = critical = exception = msg


class JayporeLoggerFactory:
    def __init__(self):
        pass

    def __call__(self, *args) -> JayporeLogger:
        return JayporeLogger()


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        # structlog.processors.StackInfoRenderer(),
        # structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=False),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
    context_class=dict,
    logger_factory=JayporeLoggerFactory(),
    cache_logger_on_first_use=False,
)
logger = structlog.get_logger()
