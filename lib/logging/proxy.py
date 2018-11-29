

class LoggerProxy(object):

    def __init__(self, log_queue, debug_var):
        self._log_queue = log_queue
        self._debug_var = debug_var

    def debug(self, msg):
        if self._debug_var.value:
            self._log_queue.put(msg)
