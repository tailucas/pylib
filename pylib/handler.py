import builtins
import logging

from weakref import WeakValueDictionary

from sentry_sdk import capture_exception
from time import sleep
from zmq.error import ZMQError, ContextTerminated, Again

from .zmq import Closable

log = logging.getLogger(APP_NAME) # type: ignore


class exception_handler(object):

    def __init__(self, name=None, closable: Closable = None):
        if name is None:
            name = self.__class__.__name__
        self.name = name
        self.closable = closable

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            return True
        log.debug(f'Handling {exc_type.__name__} with flags...')
        if exc_type is ContextTerminated:
            if self.closable:
                self.closable.close()
            else:
                log.warning(f'Received ZMQ {exc_type.__name__} but not closable. Propagating...', exc_info=True)
        elif issubclass(exc_type, ZMQError):
            log.exception(self.name)
        elif issubclass(exc_type, Exception):
            log.exception(self.name)
            capture_exception(error=(exc_type, exc_val, tb))
        return False