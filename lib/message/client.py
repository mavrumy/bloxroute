import json
import struct
from lib.message.type import MessageType


class ClientMessage(object):

    HEADER_SIZE = 8

    def __init__(self, message_type, message_data):
        self._message_type = message_type
        self._message_data = message_data

    def __str__(self):
        return "{} - {}".format(self._message_type.name, self._message_data)

    @property
    def message_type(self):
        return self._message_type

    @property
    def message_data(self):
        return self._message_data

    @property
    def data_size(self):
        return len(self._message_data)

    @property
    def message_size(self):
        return self.HEADER_SIZE + self.data_size

    def encode(self):
        message = struct.pack("II{}s".format(self.data_size), self._message_type.value, self.data_size,
                              self._message_data)
        return message

    def to_json(self):
        return json.loads(self._message_data)

    @classmethod
    def from_json(cls, message_type, json_object):
        return cls(message_type, json.dumps(json_object))

