import functools
import logging

logger = logging.getLogger(__name__)


def log_with_args(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f'ENTER {func.__name__}: args={args} kwargs={kwargs}')
        res = func(*args, **kwargs)
        logger.debug(f'EXIT {func.__name__}: args={args} kwargs={kwargs}')
        return res

    return wrapper