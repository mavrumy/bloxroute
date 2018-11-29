import struct
import json


class MessageResponse(object):

    HEADER_SIZE = 8
    OK = 1
    ERROR = 0
    _status_map = {OK: "OK", ERROR: "ERROR"}

    def __init__(self, status, response):
        self._status = status
        self._response = response

    def __str__(self):
        if self.response_size:
            return "{} - {}".format(self._status_map[self._status], self._response)
        else:
            return self._status_map[self._status]

    @property
    def status(self):
        return self._status

    @property
    def response(self):
        return self._response

    @property
    def response_size(self):
        return len(self._response)

    @property
    def message_size(self):
        return self.HEADER_SIZE + self.response_size

    def encode(self):
        message = struct.pack("II{}s".format(self.response_size), self._status, self.response_size,
                              self.response)
        return message

    @classmethod
    def from_json(cls, status, json_object):
        return cls(status, json.dumps(json_object))

