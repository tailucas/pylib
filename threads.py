import builtins
import logging
import signal
import sys
import threading
import time
import traceback

from datetime import datetime

from .aws.metrics import post_count_metric


log = logging.getLogger(APP_NAME)

# threads to interrupt
interruptable_sleep = threading.Event()
# threads to nanny
threads_tracked = set()
# shutdown flag
shutting_down = False


# noinspection PyShadowingNames
def thread_nanny(signal_handler):
    global interruptable_sleep
    global threads_tracked
    global shutting_down
    sleep_seconds = 60
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
                    # show detail about lingering non-daemon threads more often
                    sleep_seconds = 2
                    code = []
                    stack = sys._current_frames()[thread_info.ident]
                    for filename, lineno, name, line in traceback.extract_stack(stack):
                        code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
                        if line:
                            code.append("  %s" % (line.strip()))
                    for line in code:
                        log.debug(line)
        # print zmq sockets that are still alive (and blocking shutdown)
        if shutting_down:
            for s in zmq_context._sockets:
                if s and not s.closed:
                    log.debug(vars(s))
        if not shutting_down:
            thread_deficit = threads_tracked - threads_alive
            if len(thread_deficit) > 0:
                error_msg = 'A thread has died. Expected threads are [{}], ' \
                            'missing is [{}].'.format(threads_tracked, thread_deficit)
                log.fatal(error_msg)
                post_count_metric('Fatals')
                shutting_down = True
                interruptable_sleep.set()
            elif datetime.now().minute % 5 == 0:
                # zero every 5 minutes
                post_count_metric('Fatals', 0)
        else:
            # interrupt any other sleepers
            interruptable_sleep.set()
        # never spin
        time.sleep(sleep_seconds)
