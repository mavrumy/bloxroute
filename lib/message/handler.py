from lib.message.response import MessageResponse
from lib.message.type import MessageType
import Queue
import socket
from time import sleep


class MessageHandler(object):

    DEBUG_OFF = "off"
    DEBUG_ON = "on"

    def __init__(self, message, queue, client, debug_var, stop_var, logger):
        self._message = message
        self._queue = queue
        self._client = client
        self._debug_var = debug_var
        self._stop_var = stop_var
        self._logger = logger
        self._handlers = {
            MessageType.DEBUG.value: self._debug,
            MessageType.STAT.value: self._stat,
            MessageType.DEQ.value: self._deq,
            MessageType.ENQ.value: self._enq,
            MessageType.STOP.value: self._stop,
        }

    def handle(self):
        self._logger.debug("handling {} request from {}.".format(self._message.message_type.name,
                                                                 self._client.getsockname()))
        self._handlers[self._message.message_type.value]()

    def _debug(self):
        op = self._message.message_data.lower()
        self._send(MessageResponse(MessageResponse.OK, ""))
        if op == self.DEBUG_ON and not self._debug_var.value:
            self._debug_var.value = 1
            self._logger.debug("server debug trace is enabled")
        elif op == self.DEBUG_OFF and self._debug_var.value:
            self._logger.debug("server debug trace is disabled")
            self._debug_var.value = 0

    def _stat(self):
        queue_size = int(self._queue.qsize())
        response = MessageResponse(MessageResponse.OK, str(queue_size))
        self._send(response)

    def _enq(self):
        try:
            sleep(1)
            item = self._message.to_json()
            self._queue.put_nowait(item)
            response = MessageResponse(MessageResponse.OK, "")
        except ValueError:
            response = MessageResponse(MessageResponse.ERROR, "failed to enqueue item since the provided item data {} "
                                                              "is not JSON serializable".format(
                                                                self._message.message_data))
        except Queue.Full:
            response = MessageResponse(MessageResponse.ERROR, "failed to enqueue item since server queue is full")
        self._send(response)

    def _deq(self):
        try:
            item = self._queue.get_nowait()
            self._logger.debug("dequeued item {}".format(item))
            response = MessageResponse.from_json(MessageResponse.OK, item)
        except Queue.Empty:
            response = MessageResponse(MessageResponse.ERROR, "server queue is empty")
        self._send(response)

    def _stop(self):
        self._logger.debug("stopping server")
        self._stop_var.value = 1

    def _send(self, response):
        try:
            self._client.sendall(response.encode())
            self._logger.debug("successfully sent response {} to {}".format(response, self._client.getsockname()))
        except socket.error as e:
            self._logger.debug("failed to send response {} to {}, {}".format(response, self._client.getsockname(),
                                                                             e))

