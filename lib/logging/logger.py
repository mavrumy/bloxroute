import Queue
import logging
from datetime import datetime
from os.path import join, exists
from os import makedirs


class Logger(object):

    def __init__(self, log_queue, log_folder, debug_var):
        if not exists(log_folder):
            makedirs(log_folder)
        self._log_queue = log_queue
        self._logger = logging.getLogger("__main__")
        file_name = "tcp_server_{}.log".format(datetime.now().strftime("%Y%m%d%H%M%s"))
        file_path = join(log_folder, file_name)
        file_handler = logging.FileHandler(file_path)
        formatter = logging.Formatter("%(asctime)s -- %(message)s")
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)
        self._debug_var = debug_var

    def handle(self):
        while self._debug_var.value and not self._log_queue.empty():
            try:
                log_item = self._log_queue.get_nowait()
                self._logger.debug(log_item)
            except Queue.Empty:
                break
