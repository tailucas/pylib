import cronitor
import logging
import signal
import sys
import threading
import time
import traceback

from datetime import datetime

from zmq.error import ZMQError

from .aws.metrics import post_count_metric
from .zmq import try_close, zmq_sockets


log = logging.getLogger(APP_NAME)  # type: ignore

# threads to interrupt
interruptable_sleep = threading.Event()
# threads to nanny
threads_tracked = set()
# shutdown flag
shutting_down = False
# shutdown trigger exception
trigger_exception = None


def die(exception=None):
    global shutting_down
    global interruptable_sleep
    global trigger_exception
    log.debug(f'Shutting down...')
    shutting_down = True
    interruptable_sleep.set()
    # enforce latch so as not to unset later due to __main__ shutdown
    if exception is not None:
        trigger_exception = exception


def bye():
    global trigger_exception
    exit_cause = trigger_exception
    exit_code = 0
    exit_message = f'Shutdown complete.'
    if exit_cause is not None:
        exit_message += f' Exception was {exit_cause!s}.'
        exit_code = 1
    exit_message += f' Exiting with code {exit_code}.'
    log.info(exit_message)
    # flush loggers
    logging.shutdown()
    # exit process
    exit(code=exit_code)


# noinspection PyShadowingNames
def thread_nanny(signal_handler):
    global interruptable_sleep
    global threads_tracked
    global shutting_down
    shutting_down_grace_secs = APP_CONFIG.getint('app', 'shutting_down_grace_secs', fallback=30)  # type: ignore
    shutting_down_time = None
    monitor = None
    if APP_CONFIG.has_option('app', 'cronitor_monitor_key'):  # type: ignore
        monitor = cronitor.Monitor(APP_CONFIG.get('app', 'cronitor_monitor_key'))  # type: ignore
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
                    stack = sys._current_frames()[thread_info.ident]
                    for filename, lineno, name, line in traceback.extract_stack(stack):
                        code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
                        if line:
                            code.append("  %s" % (line.strip()))
                    for line in code:
                        log.debug(line)
        if not shutting_down:
            thread_deficit = threads_tracked - threads_alive
            state = 'ok'
            if len(thread_deficit) > 0:
                error_msg = f'A thread has died. Expected threads are [{threads_tracked}], ' \
                            f'missing is [{thread_deficit}].'
                log.warning(error_msg)
                post_count_metric('Fatals')
                die(exception=ResourceWarning(error_msg))
                state = 'fail'
            elif datetime.now().minute % 5 == 0:
                # zero every 5 minutes
                post_count_metric('Fatals', 0)
            if monitor is not None:
                try:
                    monitor.ping(
                        host=DEVICE_NAME, # type: ignore
                        state=state,
                        metrics={
                            'count': len(threads_alive),
                            'error_count': len(thread_deficit)
                        }
                    )
                except Exception as e:
                    log.warning(f'Problem sending cronitor ping: {e!s}')
            # don't block on the long sleep
            interruptable_sleep.wait(60)
        else:
            # interrupt any other sleepers now
            interruptable_sleep.set()
            now = int(time.time())
            if shutting_down_time is None:
                shutting_down_time = now
            if (now - shutting_down_time > shutting_down_grace_secs):
                if log.level != logging.DEBUG:
                    log.warning(f"Shutting-down duration has exceeded {shutting_down_grace_secs}s. Switching to debug logging...")
                    log.setLevel(logging.DEBUG)
                # close zmq sockets that are still alive (and blocking shutdown)
                try:
                    for s,l in zmq_sockets.items(): # type: ignore
                        try:
                            if s and not s.closed:
                                log.warning(f'Closing lingering socket {s!r} created at {l}.')
                                try_close(s)
                        except ZMQError:
                            log.debug('ZMQ error on closing socket.', exc_info=True)
                            # not interesting in this context
                            continue
                except RuntimeError:
                    # protect against "Set changed size during iteration", try again later
                    log.debug('Issue on closing lingering sockets.', exc_info=True)
        # never spin
        time.sleep(2)
