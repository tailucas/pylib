import logging
import signal
import sys
import threading
import time
import traceback

from . import app_config, log
from .tracing import shutdown

# threads to interrupt
interruptable_sleep = threading.Event()
# threads to nanny
threads_tracked: set[str] = set()
# shutdown flag
shutting_down = False
# shutdown trigger exception
trigger_exception = None


def die(exception=None):
    global shutting_down
    global interruptable_sleep
    global trigger_exception
    # enforce latch so as not to unset later due to __main__ shutdown
    if trigger_exception is None:
        trigger_exception = exception
    log.debug("Flushing OpenTelemetry...")
    shutdown()
    log.debug("Shutting down application...")
    shutting_down = True
    interruptable_sleep.set()


def bye():
    global trigger_exception
    exit_cause = trigger_exception
    exit_code = 0
    if exit_cause is not None:
        exit_code = 1
    log.debug(
        "Shutdown complete.",
        extra={
            "exit_code": exit_code,
            "exit_cause": str(exit_cause) if exit_cause is not None else None,
        },
    )
    # flush loggers
    logging.shutdown()
    # exit process
    exit(code=exit_code)


# noinspection PyShadowingNames
def thread_nanny(signal_handler):
    global interruptable_sleep
    global threads_tracked
    global shutting_down
    shutting_down_grace_secs = app_config.getint(  # noqa: F821
        "app", "shutting_down_grace_secs", fallback=30
    )  # type: ignore
    shutting_down_time = None
    while True:
        if signal_handler.last_signal == signal.SIGTERM:
            shutting_down = True
        # take stock of running threads
        threads_alive = set()
        for thread_info in threading.enumerate():
            if thread_info.is_alive():
                threads_alive.add(thread_info.getName())
                # print non-daemon threads that linger
                if shutting_down and not thread_info.daemon:
                    code = []
                    stack = sys._current_frames()[thread_info.ident]  # type: ignore
                    for filename, lineno, name, line in traceback.extract_stack(stack):
                        code.append(f'File: "{filename}", line {lineno}, in {name}')
                        if line:
                            code.append(f"  {line.strip()}")
                    for line in code:
                        log.debug(
                            "Lingering thread stack frame",
                            extra={"thread_name": thread_info.getName(), "stack_line": line},
                        )
        if not shutting_down:
            thread_deficit = threads_tracked - threads_alive
            if len(thread_deficit) > 0:
                error_msg = (
                    f"A thread has died. Expected threads are [{threads_tracked}], "
                    f"missing is [{thread_deficit}]."
                )
                log.debug(
                    "A thread has died",
                    extra={
                        "expected_threads": sorted(threads_tracked),
                        "missing_threads": sorted(thread_deficit),
                    },
                )
                die(exception=ResourceWarning(error_msg))
            # don't block on the long sleep
            interruptable_sleep.wait(60)
        else:
            # interrupt any other sleepers now
            interruptable_sleep.set()
            now = int(time.time())
            if shutting_down_time is None:
                shutting_down_time = now
            if now - shutting_down_time > shutting_down_grace_secs:
                if log.level != logging.DEBUG:
                    log.debug(
                        "Shutting-down duration has exceeded grace period. Switching to debug logging...",
                        extra={"grace_secs": shutting_down_grace_secs},
                    )
                    log.setLevel(logging.DEBUG)
                # close zmq sockets that are still alive (and blocking shutdown)
                try:
                    from zmq.error import ZMQError

                    from .zmq import try_close, zmq_sockets

                    for s, loc in zmq_sockets.items():  # type: ignore
                        try:
                            if s and not s.closed:
                                log.debug(
                                    "Closing lingering socket",
                                    extra={"socket": repr(s), "created_at": loc},
                                )
                                try_close(s)
                        except ZMQError:
                            log.debug("ZMQ error on closing socket.", exc_info=True)
                            # not interesting in this context
                            continue
                except RuntimeError:
                    # protect against "Set changed size during iteration", try again later
                    log.debug("Issue on closing lingering sockets.", exc_info=True)
                except ImportError:
                    # zmq not installed, nothing to do
                    pass
        # never spin
        time.sleep(2)
