from lib.message.client import ClientMessage
from lib.message.response import MessageResponse
from lib.message.type import MessageType
import socket
import select
import argparse
import struct


EXIT_COMMAND = "EXIT"
DEFAULT_HOST = "localhost"
BUFFER_SIZE = 1024
RESPONSE_TIMEOUT = 10


def main(host, port):
    stop_client = False
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        print("connected to server")
    except socket.error as e:
        print "connection failed - {}".format(e)
        return

    while not stop_client:
        inp = raw_input(">>")
        if not inp:
            continue
        command = inp.split(" ")[0]
        command_data = inp[len(command) + 1:]
        try:
            msg_type = MessageType[command.upper()]
        except IndexError:
            continue
        except KeyError:
            if command.upper() == EXIT_COMMAND:
                stop_client = True
                print "closing client"
            else:
                print "invalid command entered, {} doesn't exist".format(command[0])
            continue
        client_message = ClientMessage(msg_type, command_data)
        msg = client_message.encode()
        try:
            client_socket.sendall(msg)
        except socket.error as e:
            print "failed to send message ({}) to {} - {}".format(msg, host, e)
        socket_events, _, _ = select.select([client_socket], [], [], RESPONSE_TIMEOUT)
        if len(socket_events) > 0:
            if not receive(client_socket):
                print("server disconnected")
                break
        else:
            print("server response timeout reached")
    client_socket.close()


def receive(connection):
    try:
        data = connection.recv(BUFFER_SIZE)
        if not data:
            return False

        while data:
            response = parse(data)
            if response:
                print(response)
                data = data[response.message_size:]
            con_events, _, _ = select.select([connection], [], [], 0)
            if len(con_events) > 0:
                data += connection.recv(BUFFER_SIZE)
            elif response is None:
                print("invalid response received")
                data = ""
        return True
    except socket.error as e:
        print("error while receiving data from server, {}".format(e))
        return False


def parse(buf):
        buf_size = len(buf)
        if buf_size < MessageResponse.HEADER_SIZE:
            return None
        status, response_size = struct.unpack("II", buf[:MessageResponse.HEADER_SIZE])
        if response_size:
            if buf_size < MessageResponse.HEADER_SIZE + response_size:
                return None
            response = struct.unpack("{}s".format(response_size),
                                     buf[MessageResponse.HEADER_SIZE: MessageResponse.HEADER_SIZE + response_size])[0]
        else:
            response = ""
        return MessageResponse(status, response)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(prog="TCP client app")
    arg_parser.add_argument("-p", type=int, help="the server port (required)")
    arg_parser.add_argument("--host", type=str, default=DEFAULT_HOST,
                            help="the server host (default is {})".format(DEFAULT_HOST))
    args = arg_parser.parse_args()
    main(args.host, args.p)
