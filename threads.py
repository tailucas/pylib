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

# noinspection PyShadowingNames
def thread_nanny(signal_handler):
    sleep_seconds = 60
    while True:
        if signal_handler.last_signal == signal.SIGTERM:
            builtins.shutting_down = True
        threads_alive = set()
        for thread_info in threading.enumerate():
            if thread_info.is_alive():
                threads_alive.add(thread_info.getName())
                if builtins.shutting_down and not thread_info.daemon:
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
        if not builtins.shutting_down:
            thread_deficit = builtins.threads_tracked - threads_alive
            if len(thread_deficit) > 0:
                error_msg = 'A thread has died. Expected threads are [{}], ' \
                            'missing is [{}].'.format(builtins.threads_tracked, thread_deficit)
                log.fatal(error_msg)
                post_count_metric('Fatals')
                builtins.interruptable_sleep.set()
            elif datetime.now().minute % 5 == 0:
                # zero every 5 minutes
                post_count_metric('Fatals', 0)
        else:
            # interrupt any other sleepers
            builtins.interruptable_sleep.set()
        # never spin
        time.sleep(sleep_seconds)
